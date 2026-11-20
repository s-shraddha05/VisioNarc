// Pure (no imports) so it can be unit-tested with `node --test`.

export type SessionCheckOutcome = "unauthorized" | "unavailable";

/**
 * Decide what a failed "who am I?" check on page load means.
 * Only a genuine HTTP 401 from the backend means the saved token is invalid (sign out).
 * Anything else — no response, network error, proxy 5xx, timeout — means the server could not
 * answer, so the token is kept and the user can retry.
 */
export function classifySessionCheckError(error: unknown): SessionCheckOutcome {
  const status = (error as { response?: { status?: unknown } } | null)?.response?.status;
  return status === 401 ? "unauthorized" : "unavailable";
}
