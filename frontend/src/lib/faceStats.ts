/**
 * Pixel statistics computed in the browser from the captured image and MediaPipe face landmarks.
 * The image itself is never uploaded; only these numbers are. The server range-checks them but
 * cannot verify them, and labels them "browser_pixels".
 */
import type { PixelStats } from "@/lib/types";

type Pt = { x: number; y: number };

// Full eye contours from the MediaPipe Face Mesh topology.
const EYE_A = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246];
const EYE_B = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398];
const IRIS_A = [468, 469, 470, 471, 472];
const IRIS_B = [473, 474, 475, 476, 477];
const MIN_IRIS_PX = 30; // below this the pupil region cannot be resolved

function irisCircle(lm: Pt[], idx: number[], w: number, h: number) {
  const c = { x: lm[idx[0]].x * w, y: lm[idx[0]].y * h };
  const r =
    idx.slice(1).reduce((sum, i) => sum + Math.hypot(lm[i].x * w - c.x, lm[i].y * h - c.y), 0) / (idx.length - 1);
  return { ...c, r };
}

function grayAt(d: Uint8ClampedArray, i: number) {
  return 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
}

export function computePixelStats(image: CanvasImageSource, width: number, height: number, lm: Pt[]): PixelStats {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.drawImage(image, 0, 0, width, height);

  // ---- Face crop resized to 256 px wide: brightness, contrast, sharpness (Laplacian variance).
  const xs = lm.map((p) => p.x * width);
  const ys = lm.map((p) => p.y * height);
  const x0 = Math.max(0, Math.min(...xs));
  const y0 = Math.max(0, Math.min(...ys));
  const cw = Math.max(1, Math.min(width, Math.max(...xs)) - x0);
  const ch = Math.max(1, Math.min(height, Math.max(...ys)) - y0);
  const outW = 256;
  const outH = Math.max(1, Math.round((ch / cw) * outW));
  const small = document.createElement("canvas");
  small.width = outW;
  small.height = outH;
  const sctx = small.getContext("2d", { willReadFrequently: true })!;
  sctx.drawImage(canvas, x0, y0, cw, ch, 0, 0, outW, outH);
  const sd = sctx.getImageData(0, 0, outW, outH).data;
  const gray = new Float32Array(outW * outH);
  let sum = 0;
  for (let i = 0; i < gray.length; i++) {
    gray[i] = grayAt(sd, i * 4);
    sum += gray[i];
  }
  const mean = sum / gray.length;
  let varSum = 0;
  for (const g of gray) varSum += (g - mean) ** 2;
  const lap: number[] = [];
  for (let y = 1; y < outH - 1; y++) {
    for (let x = 1; x < outW - 1; x++) {
      const i = y * outW + x;
      lap.push(gray[i - 1] + gray[i + 1] + gray[i - outW] + gray[i + outW] - 4 * gray[i]);
    }
  }
  const lapMean = lap.reduce((a, b) => a + b, 0) / Math.max(1, lap.length);
  const lapVar = lap.reduce((a, b) => a + (b - lapMean) ** 2, 0) / Math.max(1, lap.length);

  // ---- Eye regions: red ratio outside the iris, and dark pupil region inside the iris.
  const full = ctx.getImageData(0, 0, width, height).data;
  const eyes = [
    { contour: EYE_A, iris: irisCircle(lm, IRIS_A, width, height) },
    { contour: EYE_B, iris: irisCircle(lm, IRIS_B, width, height) },
  ].map((e) => ({ ...e, cx: e.contour.reduce((s, i) => s + lm[i].x, 0) / e.contour.length }));
  eyes.sort((a, b) => a.cx - b.cx); // image-left first

  const perEye = eyes.map(({ contour, iris }) => {
    const mask = document.createElement("canvas");
    mask.width = width;
    mask.height = height;
    const mctx = mask.getContext("2d", { willReadFrequently: true })!;
    mctx.beginPath();
    contour.forEach((i, k) => (k ? mctx.lineTo(lm[i].x * width, lm[i].y * height) : mctx.moveTo(lm[i].x * width, lm[i].y * height)));
    mctx.closePath();
    mctx.fill();
    const bx0 = Math.max(0, Math.floor(Math.min(...contour.map((i) => lm[i].x * width))));
    const bx1 = Math.min(width - 1, Math.ceil(Math.max(...contour.map((i) => lm[i].x * width))));
    const by0 = Math.max(0, Math.floor(Math.min(...contour.map((i) => lm[i].y * height))));
    const by1 = Math.min(height - 1, Math.ceil(Math.max(...contour.map((i) => lm[i].y * height))));
    const md = mctx.getImageData(0, 0, width, height).data;

    let redSum = 0;
    let redN = 0;
    for (let y = by0; y <= by1; y++) {
      for (let x = bx0; x <= bx1; x++) {
        const i = (y * width + x) * 4;
        if (md[i + 3] < 128 || Math.hypot(x - iris.x, y - iris.y) <= iris.r) continue;
        const total = full[i] + full[i + 1] + full[i + 2];
        if (total < 30) continue; // skip near-black pixels (lashes, shadow)
        redSum += full[i] / total;
        redN++;
      }
    }

    let pupil: number | null = null;
    if (iris.r * 2 >= MIN_IRIS_PX) {
      const values: number[] = [];
      for (let y = Math.floor(iris.y - iris.r); y <= Math.ceil(iris.y + iris.r); y++) {
        for (let x = Math.floor(iris.x - iris.r); x <= Math.ceil(iris.x + iris.r); x++) {
          if (x < 0 || y < 0 || x >= width || y >= height || Math.hypot(x - iris.x, y - iris.y) > iris.r) continue;
          values.push(grayAt(full, (y * width + x) * 4));
        }
      }
      values.sort((a, b) => a - b);
      const min = values[0];
      const median = values[Math.floor(values.length / 2)];
      const threshold = min + 0.35 * (median - min);
      const dark = values.filter((v) => v <= threshold).length;
      const ratio = (2 * Math.sqrt(dark / Math.PI)) / (2 * iris.r);
      // Implausible results mean the region was not separable (e.g. dark irises, glare): report nothing.
      pupil = median - min > 15 && ratio > 0.1 && ratio < 0.9 ? ratio : null;
    }
    return { redness: redN >= 20 ? redSum / redN : null, pupil };
  });

  const round = (v: number | null, d = 4) => (v === null ? null : Number(v.toFixed(d)));
  return {
    brightness_mean: round(mean, 2)!,
    contrast_std: round(Math.min(128, Math.sqrt(varSum / gray.length)), 2)!,
    sharpness_laplacian_var: round(Math.min(100000, lapVar), 2)!,
    eye_redness_image_left: round(perEye[0].redness),
    eye_redness_image_right: round(perEye[1].redness),
    pupil_to_iris_ratio_image_left: round(perEye[0].pupil),
    pupil_to_iris_ratio_image_right: round(perEye[1].pupil),
  };
}
