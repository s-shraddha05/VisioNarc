// Pure helper (no imports) so it can be unit-tested with `node --test`.

/**
 * Timestamp for a sampled video frame, from the time the browser actually decoded after seeking
 * (video.currentTime), not the time that was requested. Returns null when the frame would not be
 * strictly later than the previous one (the browser landed on the same frame twice), so the
 * duplicate is skipped instead of sending repeated or out-of-order timestamps.
 */
export function frameTimestampMs(actualSeconds: number, previousMs: number | null): number | null {
  if (!Number.isFinite(actualSeconds) || actualSeconds < 0) return null;
  const ms = Math.round(actualSeconds * 1000);
  if (previousMs !== null && ms <= previousMs) return null;
  return ms;
}
