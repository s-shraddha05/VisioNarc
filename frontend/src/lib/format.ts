import type { SessionStatus } from "@/lib/types";

const dateTime = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
const dateOnly = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });
const relative = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

export function formatDateTime(iso: string | null | undefined): string {
  return iso ? dateTime.format(new Date(iso)) : "—";
}

export function formatDate(iso: string | null | undefined): string {
  return iso ? dateOnly.format(new Date(iso)) : "—";
}

export function formatRelative(iso: string): string {
  const seconds = Math.round((new Date(iso).getTime() - Date.now()) / 1000);
  const abs = Math.abs(seconds);
  if (abs < 60) return relative.format(seconds, "second");
  if (abs < 3600) return relative.format(Math.round(seconds / 60), "minute");
  if (abs < 86400) return relative.format(Math.round(seconds / 3600), "hour");
  return relative.format(Math.round(seconds / 86400), "day");
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatSeconds(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export const STATUS_LABELS: Record<SessionStatus, string> = {
  draft: "Draft",
  consented: "Consented",
  in_progress: "In progress",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

/** "auth.login_failed" -> "Login failed" */
export function describeAction(action: string): string {
  const labels: Record<string, string> = {
    "auth.login": "Signed in",
    "auth.login_failed": "Failed sign-in",
    "auth.account_locked": "Account locked",
    "auth.logout": "Signed out",
    "auth.password_changed": "Password changed",
    "auth.password_change_failed": "Password change rejected",
    "admin.created": "Administrator created",
    "admin.profile_updated": "Profile updated",
    "admin.password_reset_cli": "Password reset (CLI)",
    "session.created": "Analysis session created",
    "session.consent_withdrawn": "Consent withdrawn",
    "session.deleted": "Session deleted",
    "session.exported_csv": "Sessions exported (CSV)",
    "session.exported_json": "Session record exported",
  };
  if (labels[action]) return labels[action];
  const tail = action.split(".").pop() ?? action;
  return tail.charAt(0).toUpperCase() + tail.slice(1).replace(/_/g, " ");
}
