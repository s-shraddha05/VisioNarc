// Run with: npm test
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { test } from "node:test";
import { encodeWav, TARGET_RATE } from "../src/lib/audio.ts";

function tone(seconds: number, freq: number): Float32Array {
  const out = new Float32Array(Math.round(seconds * TARGET_RATE));
  for (let i = 0; i < out.length; i++) {
    const t = i / TARGET_RATE;
    const on = t % 1.6 < 1.2; // tone bursts with quiet gaps, like speech with pauses
    out[i] = on ? 0.3 * Math.sin(2 * Math.PI * freq * t) : 0.002 * Math.sin(2 * Math.PI * 37 * t);
  }
  return out;
}

test("encodeWav writes a 16 kHz mono 16-bit PCM header", async () => {
  const bytes = new DataView(await encodeWav(new Float32Array([0, 0.5, -1, 1.5]), TARGET_RATE).arrayBuffer());
  const text = (o: number) => String.fromCharCode(...[0, 1, 2, 3].map((k) => bytes.getUint8(o + k)));
  assert.equal(text(0), "RIFF");
  assert.equal(text(8), "WAVE");
  assert.equal(bytes.getUint16(20, true), 1); // PCM
  assert.equal(bytes.getUint16(22, true), 1); // mono
  assert.equal(bytes.getUint32(24, true), 16000);
  assert.equal(bytes.getUint16(34, true), 16); // bits per sample
  assert.equal(bytes.getUint32(40, true), 8); // 4 samples * 2 bytes
  assert.equal(bytes.byteLength, 44 + 8);
  // Samples are clamped to [-1, 1].
  assert.deepEqual([0, 1, 2, 3].map((i) => bytes.getInt16(44 + i * 2, true)), [0, 16383, -32768, 32767]);
});

// End-to-end format contract: the backend must accept exactly what the browser encoder produces.
const python = resolve("..", "backend", ".venv", "Scripts", "python.exe");
test("backend decodes and measures the frontend-encoded WAV", { skip: !existsSync(python) && "backend venv not found" }, async () => {
  const dir = mkdtempSync(join(tmpdir(), "visonarc-wav-"));
  try {
    const file = join(dir, "tone.wav");
    writeFileSync(file, Buffer.from(await encodeWav(tone(4, 220), TARGET_RATE).arrayBuffer()));
    const code =
      "import sys, json; from app.analysis.voice import decode_wav, extract_voice_features as f; " +
      "r = f(decode_wav(open(sys.argv[1], 'rb').read())); print(json.dumps({'f0': r.features['f0_median_hz'], 'pauses': r.features['pause_count'], 'reliable': r.is_reliable}))";
    const out = JSON.parse(execFileSync(python, ["-c", code, file], { cwd: resolve("..", "backend") }).toString());
    assert.ok(Math.abs(out.f0 - 220) < 5, `F0 ${out.f0}`);
    assert.ok(out.pauses >= 1);
    assert.equal(out.reliable, true);
  } finally {
    rmSync(dir, { recursive: true, force: true }); // synthetic test audio only; removed immediately
  }
});
