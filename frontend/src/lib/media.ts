// Client-side checks for usability only. The backend must re-validate every upload (Phase 3).

export interface MediaRules {
  accept: string[]; // MIME types
  extensions: string[];
  maxBytes: number;
  minSeconds?: number;
  maxSeconds?: number;
  minWidth?: number;
  minHeight?: number;
}

export const IMAGE_RULES: MediaRules = {
  accept: ["image/jpeg", "image/png", "image/webp"],
  extensions: [".jpg", ".jpeg", ".png", ".webp"],
  maxBytes: 10 * 1024 * 1024,
  minWidth: 320,
  minHeight: 240,
};

export const VIDEO_RULES: MediaRules = {
  accept: ["video/mp4", "video/webm", "video/quicktime"],
  extensions: [".mp4", ".webm", ".mov"],
  maxBytes: 50 * 1024 * 1024,
  minSeconds: 5,
  maxSeconds: 60,
};

export const AUDIO_RULES: MediaRules = {
  accept: ["audio/wav", "audio/x-wav", "audio/wave", "audio/mpeg", "audio/webm", "audio/ogg", "audio/mp4", "audio/x-m4a"],
  extensions: [".wav", ".mp3", ".webm", ".ogg", ".m4a"],
  maxBytes: 20 * 1024 * 1024,
  minSeconds: 3,
  maxSeconds: 60,
};

export interface MediaInfo {
  width?: number;
  height?: number;
  durationSeconds?: number;
}

function hasAllowedType(file: File, rules: MediaRules) {
  const name = file.name.toLowerCase();
  // Some browsers report codecs ("audio/webm;codecs=opus") or an empty type for recordings.
  const mime = file.type.split(";")[0];
  return rules.accept.includes(mime) || rules.extensions.some((ext) => name.endsWith(ext));
}

function readImage(url: string): Promise<MediaInfo> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => reject(new Error("The file could not be decoded as an image."));
    img.src = url;
  });
}

function readDuration(url: string, kind: "video" | "audio"): Promise<MediaInfo> {
  return new Promise((resolve, reject) => {
    const el = document.createElement(kind);
    el.preload = "metadata";
    el.onloadedmetadata = () => {
      // MediaRecorder webm files report Infinity until seeked; force the browser to compute it.
      if (el.duration === Infinity) {
        el.currentTime = 1e7;
        el.ontimeupdate = () => {
          el.ontimeupdate = null;
          resolve({ durationSeconds: el.duration, ...(kind === "video" ? dims(el as HTMLVideoElement) : {}) });
        };
        return;
      }
      resolve({ durationSeconds: el.duration, ...(kind === "video" ? dims(el as HTMLVideoElement) : {}) });
    };
    el.onerror = () => reject(new Error(`The file could not be decoded as ${kind}.`));
    el.src = url;
  });
}

function dims(v: HTMLVideoElement): MediaInfo {
  return { width: v.videoWidth, height: v.videoHeight };
}

/** Returns media info or throws an Error whose message is suitable for display. */
export async function validateMedia(
  file: Blob,
  name: string,
  kind: "image" | "video" | "audio",
  rules: MediaRules,
): Promise<MediaInfo> {
  const asFile = file instanceof File ? file : new File([file], name, { type: file.type });
  if (!hasAllowedType(asFile, rules)) {
    throw new Error(`Unsupported file type. Allowed: ${rules.extensions.join(", ")}.`);
  }
  if (asFile.size === 0) throw new Error("The file is empty.");
  if (asFile.size > rules.maxBytes) {
    throw new Error(`File is too large (max ${Math.round(rules.maxBytes / (1024 * 1024))} MB).`);
  }
  const url = URL.createObjectURL(asFile);
  try {
    const info = kind === "image" ? await readImage(url) : await readDuration(url, kind);
    if (rules.minWidth && info.width !== undefined && info.height !== undefined) {
      if (info.width < rules.minWidth || info.height < (rules.minHeight ?? 0)) {
        throw new Error(`Resolution ${info.width}×${info.height} is too low (min ${rules.minWidth}×${rules.minHeight}).`);
      }
    }
    if (info.durationSeconds !== undefined && Number.isFinite(info.durationSeconds)) {
      if (rules.minSeconds && info.durationSeconds < rules.minSeconds) {
        throw new Error(`Recording is too short (${info.durationSeconds.toFixed(1)} s; min ${rules.minSeconds} s).`);
      }
      if (rules.maxSeconds && info.durationSeconds > rules.maxSeconds + 0.5) {
        throw new Error(`Recording is too long (${info.durationSeconds.toFixed(0)} s; max ${rules.maxSeconds} s).`);
      }
    }
    return info;
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function mediaErrorMessage(err: unknown): string {
  if (err instanceof DOMException) {
    switch (err.name) {
      case "NotAllowedError":
        return "Permission was denied. Allow camera/microphone access in the browser's site settings and try again.";
      case "NotFoundError":
        return "No suitable camera or microphone was found on this device.";
      case "NotReadableError":
        return "The device is in use by another application. Close it and try again.";
      case "SecurityError":
        return "Media capture needs a secure context (https or localhost).";
      default:
        return err.message || err.name;
    }
  }
  return err instanceof Error ? err.message : "The device could not be started.";
}

export const mediaSupported = () =>
  typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

export const recorderSupported = () => typeof window !== "undefined" && "MediaRecorder" in window;

export function pickRecorderMime(kind: "video" | "audio"): string | undefined {
  const candidates =
    kind === "video"
      ? ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm", "video/mp4"]
      : ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return candidates.find((m) => MediaRecorder.isTypeSupported(m));
}
