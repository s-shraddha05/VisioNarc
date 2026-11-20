import assert from "node:assert/strict";
import { test } from "node:test";
import { frameTimestampMs } from "../src/lib/frameTimes.ts";

test("uses the decoded frame time, rounded to ms", () => {
  assert.equal(frameTimestampMs(0, null), 0);
  assert.equal(frameTimestampMs(0.0667, 0), 67);
  assert.equal(frameTimestampMs(1.2004, 1133), 1200);
});

test("skips repeated or backwards frames so timestamps stay strictly increasing", () => {
  assert.equal(frameTimestampMs(0.5, 500), null);
  assert.equal(frameTimestampMs(0.4999, 500), null);
  const actual = [0, 0.066, 0.066, 0.133, 0.2, 0.199, 0.266];
  const out: number[] = [];
  let prev: number | null = null;
  for (const s of actual) {
    const ms = frameTimestampMs(s, prev);
    if (ms !== null) out.push((prev = ms));
  }
  assert.deepEqual(out, [0, 66, 133, 200, 266]);
});

test("rejects invalid times", () => {
  assert.equal(frameTimestampMs(Number.NaN, null), null);
  assert.equal(frameTimestampMs(Number.POSITIVE_INFINITY, null), null);
  assert.equal(frameTimestampMs(-1, null), null);
});
