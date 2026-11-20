import { Camera, Upload } from "lucide-react";
import { ModalityWorkspace, type AnalyzeFn, type CapturedMedia } from "@/components/capture/ModalityWorkspace";
import { UploadTab, useMediaValidation } from "@/components/capture/ValidatedInput";
import { WebcamPhoto } from "@/components/capture/WebcamPhoto";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { computePixelStats } from "@/lib/faceStats";
import { IMAGE_RULES } from "@/lib/media";
import type { FacialMeasurement } from "@/lib/types";
import { getFaceLandmarker } from "@/lib/vision";

// Must match backend/app/analysis/face.py EXPRESSION_KEYS.
const EXPRESSION_KEYS = new Set([
  "eyeBlinkLeft", "eyeBlinkRight", "eyeSquintLeft", "eyeSquintRight", "eyeWideLeft", "eyeWideRight",
  "browDownLeft", "browDownRight", "jawOpen", "mouthSmileLeft", "mouthSmileRight",
]);
const MAX_ANALYSIS_SIDE = 1600; // large photos are downscaled in memory before measuring

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("The image could not be decoded."));
    img.src = url;
  });
}

const analyzeFace: AnalyzeFn = async (media, sessionId, progress) => {
  progress("Loading face model…");
  const landmarker = await getFaceLandmarker();
  const original = await loadImage(media.url);
  const scale = Math.min(1, MAX_ANALYSIS_SIDE / Math.max(original.naturalWidth, original.naturalHeight));
  const width = Math.round(original.naturalWidth * scale);
  const height = Math.round(original.naturalHeight * scale);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  canvas.getContext("2d")!.drawImage(original, 0, 0, width, height);

  progress("Detecting face landmarks…");
  const result = landmarker.detect(canvas);
  if (result.faceLandmarks.length === 0) {
    throw new Error("No face was detected. Use a clear, front-facing photo with the whole face visible.");
  }
  if (result.faceLandmarks.length > 1) {
    throw new Error("More than one face was detected. Capture one person only.");
  }
  const landmarks = result.faceLandmarks[0];
  if (landmarks.length !== 478) throw new Error(`Unexpected number of face landmarks (${landmarks.length}).`);

  progress("Measuring image quality…");
  const pixelStats = computePixelStats(canvas, width, height, landmarks);
  const expressions = Object.fromEntries(
    (result.faceBlendshapes[0]?.categories ?? [])
      .filter((c) => EXPRESSION_KEYS.has(c.categoryName))
      .map((c) => [c.categoryName, Number(Math.min(1, Math.max(0, c.score)).toFixed(4))]),
  );

  progress("Saving measurements…");
  return api.analyzeFace(sessionId, {
    source: media.origin === "webcam" ? "webcam" : "upload",
    image_width: width,
    image_height: height,
    landmarks: landmarks.map((p) => [p.x, p.y, p.z]),
    pixel_stats: pixelStats,
    expressions,
  });
};

function WebcamTab({ onMedia }: { onMedia: (m: CapturedMedia) => void }) {
  const { accept, status, checking } = useMediaValidation("image", IMAGE_RULES, onMedia);
  return (
    <div className="space-y-3">
      <WebcamPhoto disabled={checking} onCapture={(blob) => accept(blob, "webcam", "webcam.jpg")} />
      {status}
    </div>
  );
}

export function FaceAnalysisPage() {
  return (
    <ModalityWorkspace
      modality="face"
      title="Face analysis"
      description="Capture or upload a front-facing photo. Face landmarks are detected in this browser; the server computes geometric measurements from them."
      tabs={[
        {
          id: "upload",
          label: "Upload image",
          icon: <Upload />,
          render: (onMedia) => <UploadTab kind="image" rules={IMAGE_RULES} label="Choose an image" onMedia={onMedia} />,
        },
        { id: "webcam", label: "Webcam", icon: <Camera />, render: (onMedia) => <WebcamTab onMedia={onMedia} /> },
      ]}
      dataFlow={
        <>
          <strong>The photo never leaves this browser.</strong> MediaPipe runs locally; only the 478 landmark
          coordinates, a few image statistics (brightness, sharpness, eye-region colour ratios) and expression
          coefficients are sent to the server.
        </>
      }
      renderPreview={(m) => (
        <img src={m.url} alt="Captured face for analysis" className="aspect-[4/3] w-full rounded-lg border object-cover" />
      )}
      measurementsOf={(s) => s.facial_measurements}
      renderMeasurement={(m) => {
        const f = m as FacialMeasurement;
        return <Badge variant={f.face_detected ? "default" : "destructive"}>{f.face_detected ? "Face found" : "No face"}</Badge>;
      }}
      onAnalyze={analyzeFace}
    />
  );
}
