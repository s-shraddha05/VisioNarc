import assert from "node:assert/strict";
import { test } from "node:test";
import { classifySessionCheckError } from "../src/auth/sessionCheck.ts";

test("only a genuine 401 signs the user out", () => {
  assert.equal(classifySessionCheckError({ response: { status: 401 } }), "unauthorized");
});

test("backend or network failures keep the session (regression: reload while backend down)", () => {
  // Axios network error / ECONNREFUSED: no response at all.
  assert.equal(classifySessionCheckError({ message: "Network Error" }), "unavailable");
  // Vite dev proxy answering for a stopped backend.
  assert.equal(classifySessionCheckError({ response: { status: 500, data: "" } }), "unavailable");
  assert.equal(classifySessionCheckError({ response: { status: 502 } }), "unavailable");
  assert.equal(classifySessionCheckError({ response: { status: 503 } }), "unavailable"); // DB down
  assert.equal(classifySessionCheckError(new Error("timeout of 20000ms exceeded")), "unavailable");
  assert.equal(classifySessionCheckError(null), "unavailable");
});

test("403 or other client errors are not treated as sign-out either", () => {
  assert.equal(classifySessionCheckError({ response: { status: 403 } }), "unavailable");
});
