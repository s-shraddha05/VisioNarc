import { Camera, CameraOff, Loader2, Video } from "lucide-react";
import { useEffect, useRef } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useMediaStream } from "@/hooks/useMediaStream";

/** Live webcam preview with a single-frame capture. The frame never leaves the browser here. */
export function WebcamPhoto({ disabled, onCapture }: { disabled?: boolean; onCapture: (blob: Blob) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const { stream, error, starting, start, stop } = useMediaStream({
    video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
    audio: false,
  });

  useEffect(() => {
    if (videoRef.current) videoRef.current.srcObject = stream;
  }, [stream]);

  function capture() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (blob) {
        onCapture(blob);
        stop();
      }
    }, "image/jpeg", 0.92);
  }

  return (
    <div className="space-y-3">
      <div className="relative aspect-video overflow-hidden rounded-xl border bg-[oklch(0.2_0.02_250)]">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={stream ? "size-full -scale-x-100 object-cover" : "hidden"}
          aria-label="Live camera preview"
        />
        {!stream && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-sm text-white/70">
            <CameraOff className="size-6" />
            Camera is off
          </div>
        )}
        {stream && (
          <div className="pointer-events-none absolute inset-[12%] rounded-[45%] border-2 border-dashed border-white/50" />
        )}
      </div>
      {error && <Alert variant="destructive">{error}</Alert>}
      <div className="flex flex-wrap gap-2">
        {!stream ? (
          <Button onClick={start} disabled={disabled || starting}>
            {starting ? <Loader2 className="animate-spin" /> : <Video />} Start camera
          </Button>
        ) : (
          <>
            <Button onClick={capture} disabled={disabled}>
              <Camera /> Capture photo
            </Button>
            <Button variant="outline" onClick={stop}>
              <CameraOff /> Stop camera
            </Button>
          </>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        Centre the face inside the guide, look at the camera and use even, front-facing light.
      </p>
    </div>
  );
}
