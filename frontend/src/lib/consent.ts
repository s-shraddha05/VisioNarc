// Consent wording v1.0. The backend stores CONSENT_TEXT_VERSION = "1.0" with every consent record;
// bump both together if this text changes.
export const CONSENT_VERSION = "1.0";

export const CONSENT_POINTS = [
  "This is an experimental academic research prototype. It is not a medical, legal or forensic test.",
  "Facial appearance, voice and movement cannot prove drug consumption. No result will label you as a drug user.",
  "Only the modalities you tick below may be captured. You can decline any of them.",
  "By default only numeric features are kept; raw photos, video and audio are discarded after processing.",
  "Records are kept until the retention date shown on the session and can be deleted earlier on request.",
  "You may withdraw consent at any time. Withdrawal deletes all measurements and results for the session.",
];
