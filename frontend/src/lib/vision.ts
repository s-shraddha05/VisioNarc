import type { FaceLandmarker, PoseLandmarker } from "@mediapipe/tasks-vision";

// Served from frontend/public/mediapipe (installed by scripts/setup_mediapipe.ps1, git-ignored).
const WASM_BASE = "/mediapipe/wasm";
const FACE_MODEL = "/mediapipe/models/face_landmarker.task";
const POSE_MODEL = "/mediapipe/models/pose_landmarker_lite.task";

const MISSING =
  "MediaPipe files are not installed. Run: powershell -ExecutionPolicy Bypass -File .\\scripts\\setup_mediapipe.ps1";

async function assertAsset(path: string) {
  const res = await fetch(path, { method: "HEAD" }).catch(() => null);
  // Vite's SPA fallback answers unknown paths with index.html (text/html), so check the type too.
  if (!res || !res.ok || (res.headers.get("content-type") ?? "").includes("text/html")) throw new Error(MISSING);
}

let filesetPromise: ReturnType<typeof loadFileset> | null = null;
async function loadFileset() {
  await Promise.all([assertAsset(`${WASM_BASE}/vision_wasm_internal.wasm`), assertAsset(FACE_MODEL), assertAsset(POSE_MODEL)]);
  // Loaded on demand so the ~0.2 MB library is not part of the main bundle.
  const mp = await import("@mediapipe/tasks-vision");
  return { mp, fileset: await mp.FilesetResolver.forVisionTasks(WASM_BASE) };
}

function fileset() {
  filesetPromise ??= loadFileset().catch((err) => {
    filesetPromise = null; // allow retry after the user installs the assets
    throw err;
  });
  return filesetPromise;
}

let facePromise: Promise<FaceLandmarker> | null = null;
export function getFaceLandmarker(): Promise<FaceLandmarker> {
  facePromise ??= fileset()
    .then(({ mp, fileset }) =>
      mp.FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: FACE_MODEL, delegate: "CPU" },
        runningMode: "IMAGE",
        numFaces: 2, // detect a second face so we can refuse multi-person images
        outputFaceBlendshapes: true,
      }),
    )
    .catch((err) => {
      facePromise = null;
      throw err;
    });
  return facePromise;
}

/** A fresh VIDEO-mode instance per clip: timestamps must restart from zero for each video. */
export async function createPoseLandmarker(): Promise<PoseLandmarker> {
  const { mp, fileset: fs } = await fileset();
  return mp.PoseLandmarker.createFromOptions(fs, {
    baseOptions: { modelAssetPath: POSE_MODEL, delegate: "CPU" },
    runningMode: "VIDEO",
    numPoses: 1,
  });
}
