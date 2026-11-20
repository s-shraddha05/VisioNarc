import { Upload, Video } from "lucide-react";
import { MediaRecorderPanel } from "@/components/capture/MediaRecorderPanel";
import { ModalityWorkspace, type AnalyzeFn, type CapturedMedia } from "@/components/capture/ModalityWorkspace";
import { UploadTab, useMediaValidation } from "@/components/capture/ValidatedInput";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { VIDEO_RULES } from "@/lib/media";
import { extractPoseFrames } from "@/lib/pose";
import type { MotionMeasurement } from "@/lib/types";

const analyzeMotion: AnalyzeFn = async (media, sessionId, progress) => {
  progress("Loading pose model…");
  const submission = await extractPoseFrames(media.url, media.origin === "upload" ? "upload" : "webcam", (f) =>
    progress(`Tracking pose… ${Math.round(f * 100)} %`),
  );
  const withPose = submission.frames.filter((f) => f.landmarks).length;
  if (withPose < 10) {
    throw new Error("A person was detected in fewer than 10 frames. Keep the head and shoulders in view and try again.");
  }
  progress("Saving measurements…");
  return api.analyzeMotion(sessionId, submission);
};

function RecordTab({ onMedia }: { onMedia: (m: CapturedMedia) => void }) {
  const { accept, status, checking } = useMediaValidation("video", VIDEO_RULES, onMedia);
  return (
    <div className="space-y-3">
      <MediaRecorderPanel
        kind="video"
        minSeconds={VIDEO_RULES.minSeconds!}
        maxSeconds={VIDEO_RULES.maxSeconds!}
        disabled={checking}
        onRecorded={(blob) => accept(blob, "webcam", "motion.webm")}
      />
      {status}
    </div>
  );
}

export function MotionAnalysisPage() {
  return (
    <ModalityWorkspace
      modality="motion"
      title="Motion analysis"
      description="Record or upload a short clip with head and shoulders in frame. Body pose is tracked in this browser at 15 frames per second; the server computes movement measurements."
      tabs={[
        { id: "record", label: "Webcam", icon: <Video />, render: (onMedia) => <RecordTab onMedia={onMedia} /> },
        {
          id: "upload",
          label: "Upload video",
          icon: <Upload />,
          render: (onMedia) => <UploadTab kind="video" rules={VIDEO_RULES} label="Choose a video" onMedia={onMedia} />,
        },
      ]}
      dataFlow={
        <>
          <strong>The video never leaves this browser.</strong> MediaPipe tracks 33 body landmarks locally; only
          their coordinates and timestamps are sent to the server.
        </>
      }
      renderPreview={(m) => (
        <video src={m.url} controls playsInline className="aspect-video w-full rounded-lg border bg-black" aria-label="Recorded motion clip" />
      )}
      measurementsOf={(s) => s.motion_measurements}
      renderMeasurement={(m) => {
        const mm = m as MotionMeasurement;
        const pct = mm.frames_processed ? Math.round((mm.frames_with_pose / mm.frames_processed) * 100) : 0;
        return <Badge variant="neutral">Pose tracked {pct}%</Badge>;
      }}
      onAnalyze={analyzeMotion}
    />
  );
}
