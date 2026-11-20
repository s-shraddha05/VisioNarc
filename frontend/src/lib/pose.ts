import { frameTimestampMs } from "@/lib/frameTimes";
import { createPoseLandmarker } from "@/lib/vision";
import type { MotionSubmission, PoseFrame } from "@/lib/types";

const SAMPLE_FPS = 15;
const MAX_SECONDS = 60;

function once(el: HTMLMediaElement, event: string) {
  return new Promise<void>((resolve, reject) => {
    const ok = () => {
      el.removeEventListener("error", fail);
      resolve();
    };
    const fail = () => {
      el.removeEventListener(event, ok);
      reject(new Error("The video could not be read by the browser."));
    };
    el.addEventListener(event, ok, { once: true });
    el.addEventListener("error", fail, { once: true });
  });
}

/**
 * Run MediaPipe Pose on a local video at 15 frames per second. Only landmark coordinates are
 * returned; the video never leaves the browser.
 */
export async function extractPoseFrames(
  url: string,
  source: MotionSubmission["source"],
  onProgress: (fraction: number) => void,
): Promise<MotionSubmission> {
  const landmarker = await createPoseLandmarker();
  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.preload = "auto";
  video.src = url;
  try {
    await once(video, "loadeddata");
    let duration = video.duration;
    if (!Number.isFinite(duration)) {
      // MediaRecorder WebM files report Infinity until the browser has seeked to the end.
      video.currentTime = 1e7;
      await once(video, "seeked");
      duration = video.duration;
    }
    duration = Math.min(duration, MAX_SECONDS);
    const frames: PoseFrame[] = [];
    const total = Math.floor(duration * SAMPLE_FPS);
    let previousMs: number | null = null;
    for (let k = 0; k <= total; k++) {
      video.currentTime = Math.min(k / SAMPLE_FPS, Math.max(0, duration - 0.001));
      await once(video, "seeked");
      // Use the time of the frame the browser actually decoded, and skip repeats.
      const tMs = frameTimestampMs(video.currentTime, previousMs);
      onProgress(k / total);
      if (tMs === null) continue;
      previousMs = tMs;
      const result = landmarker.detectForVideo(video, tMs + 1); // MediaPipe needs increasing, non-zero timestamps
      const pose = result.landmarks[0];
      frames.push({
        t_ms: tMs,
        landmarks: pose ? pose.map((p) => [p.x, p.y, p.z, Math.min(1, Math.max(0, p.visibility ?? 0))]) : null,
      });
    }
    return { source, video_width: video.videoWidth, video_height: video.videoHeight, frames };
  } finally {
    landmarker.close();
    video.removeAttribute("src");
    video.load();
  }
}
