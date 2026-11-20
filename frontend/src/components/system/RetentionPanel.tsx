import { CalendarClock, Eye, Loader2, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "@/components/common/States";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { PurgeResult, RetentionPreview } from "@/lib/types";

/** Preview sessions past their retention date and purge them after explicit confirmation. */
export function RetentionPanel() {
  const [preview, setPreview] = useState<RetentionPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [purging, setPurging] = useState(false);
  const [purgeError, setPurgeError] = useState<string | null>(null);
  const [result, setResult] = useState<PurgeResult | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setPreview(await api.retentionPreview());
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function purge() {
    if (!preview) return;
    setPurging(true);
    setPurgeError(null);
    try {
      setResult(await api.retentionPurge(preview.sessions.map((s) => s.id)));
      setConfirmOpen(false);
      setPreview(await api.retentionPreview());
    } catch (err) {
      setPurgeError(errorMessage(err));
    } finally {
      setPurging(false);
    }
  }

  const sessions = preview?.sessions ?? [];
  const dependents = sessions.reduce(
    (n, s) => n + s.consent_records + s.face_measurements + s.motion_measurements + s.voice_measurements + s.combined_records,
    0,
  );

  return (
    <Card className="xl:col-span-2">
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-3 space-y-0">
        <div className="space-y-1.5">
          <CardTitle className="flex items-center gap-2">
            <CalendarClock className="size-5 text-primary" /> Retention purge
          </CardTitle>
          <CardDescription className="max-w-2xl">
            Sessions past their “retain until” date can be deleted with their consent record, measurements and saved
            combined records. Deletion is permanent; recovery is only possible from a database backup
            (python -m scripts.backup_db).
          </CardDescription>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          {loading ? <Loader2 className="animate-spin" /> : <Eye />} Preview expired sessions
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <Alert variant="destructive">{error}</Alert>}
        {result && (
          <Alert>
            Deleted {result.deleted.length} session{result.deleted.length === 1 ? "" : "s"}
            {result.skipped_ids.length ? `; ${result.skipped_ids.length} skipped because they were no longer expired` : ""}.
          </Alert>
        )}
        {preview && (
          <p className="text-xs text-muted-foreground">
            Checked {formatDateTime(preview.checked_at)} · default retention {preview.retention_days} days · automatic purge{" "}
            {preview.auto_purge_enabled ? `on (every ${preview.interval_hours} h)` : "off (RETENTION_AUTO_PURGE=false)"}
            {preview.last_automatic_run &&
              ` · last automatic run ${formatDateTime(preview.last_automatic_run.at)}: ${
                preview.last_automatic_run.error ? `failed (${preview.last_automatic_run.error})` : `${preview.last_automatic_run.deleted} deleted`
              }`}
          </p>
        )}
        {preview &&
          (sessions.length === 0 ? (
            <EmptyState title="No sessions are past their retention date" className="py-8" />
          ) : (
            <>
              <div className="relative overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="py-2 pr-3 font-medium">Session</th>
                      <th className="py-2 pr-3 font-medium">Retain until</th>
                      <th className="py-2 pr-3 font-medium">Status</th>
                      <th className="py-2 font-medium">Dependent records</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {sessions.map((s) => (
                      <tr key={s.id}>
                        <td className="py-2 pr-3">
                          <Link to={`/history/${s.id}`} className="font-mono text-xs hover:text-primary">
                            {s.reference_code}
                          </Link>
                          <span className="block text-xs text-muted-foreground">{s.subject_label}</span>
                        </td>
                        <td className="py-2 pr-3">{formatDateTime(s.retain_until)}</td>
                        <td className="py-2 pr-3 capitalize">{s.status.replace("_", " ")}</td>
                        <td className="py-2 text-xs text-muted-foreground">
                          consent {s.consent_records} · face {s.face_measurements} · motion {s.motion_measurements} · voice{" "}
                          {s.voice_measurements} · combined {s.combined_records}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
                <Trash2 /> Purge {sessions.length} session{sessions.length === 1 ? "" : "s"}
              </Button>
            </>
          ))}
      </CardContent>
      <ConfirmDialog
        open={confirmOpen}
        title={`Permanently delete ${sessions.length} expired session${sessions.length === 1 ? "" : "s"}?`}
        description={`This deletes the sessions listed above and ${dependents} dependent record(s). Only sessions that are still past their retention date when you confirm are deleted. This cannot be undone without a backup.`}
        confirmLabel="Purge permanently"
        confirmText="PURGE"
        destructive
        busy={purging}
        error={purgeError}
        onConfirm={purge}
        onCancel={() => {
          setConfirmOpen(false);
          setPurgeError(null);
        }}
      />
    </Card>
  );
}
