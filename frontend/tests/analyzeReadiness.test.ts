// Run with: npm test   (Node's built-in test runner; no extra dependencies)
import assert from "node:assert/strict";
import { test } from "node:test";
import { analyzeBlockers, type ReadinessInput } from "../src/lib/analyzeReadiness.ts";

const ready: ReadinessInput = {
  modality: "voice",
  capabilitiesState: "ready",
  engineAvailable: true,
  sessionSelected: true,
  sessionProblem: null,
  hasMedia: true,
  needsConfirmation: true,
  confirmed: true,
  busy: false,
};

test("ready when every condition is met", () => {
  assert.deepEqual(analyzeBlockers(ready), []);
});

test("no session selected is explained (the silent cause of the voice-button bug)", () => {
  assert.deepEqual(analyzeBlockers({ ...ready, sessionSelected: false }), ["Select an analysis session in step 1."]);
});

test("session problems are shown next to the button", () => {
  const problem = "This session is completed and no longer accepts captures.";
  assert.deepEqual(analyzeBlockers({ ...ready, sessionProblem: problem }), [problem]);
});

test("voice upload confirmation is required before upload", () => {
  assert.deepEqual(analyzeBlockers({ ...ready, confirmed: false }), ["Tick the upload confirmation above."]);
  // Face/motion do not need it.
  assert.deepEqual(analyzeBlockers({ ...ready, modality: "face", needsConfirmation: false, confirmed: false }), []);
});

test("capability loading/failure and missing engine are explained", () => {
  assert.match(analyzeBlockers({ ...ready, capabilitiesState: "loading" })[0], /Checking/);
  assert.match(analyzeBlockers({ ...ready, capabilitiesState: "error" })[0], /Could not reach the server/);
  assert.match(analyzeBlockers({ ...ready, engineAvailable: false })[0], /voice analysis is not installed/);
});

test("multiple reasons are listed in fix order", () => {
  const reasons = analyzeBlockers({ ...ready, sessionSelected: false, hasMedia: false });
  assert.deepEqual(reasons, ["Select an analysis session in step 1.", "Capture or upload in step 2."]);
});

test("while running, the button shows progress instead of reasons", () => {
  assert.deepEqual(analyzeBlockers({ ...ready, busy: true, confirmed: false }), []);
});
