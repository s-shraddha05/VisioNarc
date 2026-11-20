// Why the "Run … analysis" button is disabled, in plain words. Pure (no imports) so it can be
// unit-tested with `node --test` without a browser or test framework.

export interface ReadinessInput {
  modality: "face" | "motion" | "voice";
  capabilitiesState: "loading" | "error" | "ready";
  engineAvailable: boolean;
  sessionSelected: boolean;
  sessionProblem: string | null;
  hasMedia: boolean;
  needsConfirmation: boolean;
  confirmed: boolean;
  busy: boolean;
}

/** Every reason the analysis cannot start right now, in the order the user should fix them. Empty = ready. */
export function analyzeBlockers(i: ReadinessInput): string[] {
  if (i.busy) return []; // the button shows live progress instead
  const reasons: string[] = [];
  if (i.capabilitiesState === "loading") reasons.push("Checking which analyses the server supports…");
  else if (i.capabilitiesState === "error") reasons.push("Could not reach the server to check analysis support.");
  else if (!i.engineAvailable) reasons.push(`The server reports that ${i.modality} analysis is not installed.`);
  if (!i.sessionSelected) reasons.push("Select an analysis session in step 1.");
  else if (i.sessionProblem) reasons.push(i.sessionProblem);
  if (!i.hasMedia) reasons.push("Capture or upload in step 2.");
  else if (i.needsConfirmation && !i.confirmed) reasons.push("Tick the upload confirmation above.");
  return reasons;
}
