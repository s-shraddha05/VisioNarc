// Camera/microphone permission and device failures shown to the user (lib/media.ts).
import assert from "node:assert/strict";
import { test } from "node:test";
import { mediaErrorMessage } from "../src/lib/media.ts";

const err = (name: string, message = "") => new DOMException(message, name);

test("permission denied explains how to allow access", () => {
  assert.match(mediaErrorMessage(err("NotAllowedError")), /Permission was denied/);
  assert.match(mediaErrorMessage(err("NotAllowedError")), /site settings/);
});

test("missing or busy devices and insecure origins are explained", () => {
  assert.match(mediaErrorMessage(err("NotFoundError")), /No suitable camera or microphone/);
  assert.match(mediaErrorMessage(err("NotReadableError")), /in use by another application/);
  assert.match(mediaErrorMessage(err("SecurityError")), /secure context/);
});

test("unknown errors fall back to a readable message", () => {
  assert.equal(mediaErrorMessage(err("AbortError", "Starting videoinput failed")), "Starting videoinput failed");
  assert.equal(mediaErrorMessage(new Error("boom")), "boom");
  assert.equal(mediaErrorMessage("weird"), "The device could not be started.");
});
