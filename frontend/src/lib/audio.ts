/** Convert any browser-decodable recording (webm/opus, mp3, m4a, wav…) to 16 kHz mono 16-bit PCM WAV. */
export const TARGET_RATE = 16000;

export async function toWav16kMono(blob: Blob): Promise<Blob> {
  const encoded = await blob.arrayBuffer();
  const ctx = new AudioContext();
  let decoded: AudioBuffer;
  try {
    decoded = await ctx.decodeAudioData(encoded);
  } catch {
    throw new Error("This audio file could not be decoded by the browser. Try WAV or MP3.");
  } finally {
    void ctx.close();
  }
  const length = Math.ceil(decoded.duration * TARGET_RATE);
  if (!Number.isFinite(length) || length <= 0) {
    throw new Error("The recording contains no audio. Record again and check that the microphone is not muted.");
  }
  try {
    const offline = new OfflineAudioContext(1, length, TARGET_RATE);
    const source = offline.createBufferSource();
    source.buffer = decoded; // multi-channel input is down-mixed to mono by the 1-channel destination
    source.connect(offline.destination);
    source.start();
    const rendered = await offline.startRendering();
    return encodeWav(rendered.getChannelData(0), TARGET_RATE);
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    throw new Error(`The recording could not be converted to 16 kHz WAV (${detail}).`);
  }
}

/** 16-bit PCM mono WAV (44-byte header). Exported for unit tests. */
export function encodeWav(samples: Float32Array, rate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const write = (offset: number, text: string) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  write(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  write(8, "WAVE");
  write(12, "fmt ");
  view.setUint32(16, 16, true); // PCM chunk size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  write(36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}
