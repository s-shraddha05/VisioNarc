import { FlaskConical, Loader2, Play, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { ErrorState, LoadingState } from "@/components/common/States";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useApi } from "@/hooks/useApi";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { ScreeningResult } from "@/lib/types";

/**
 * Experimental screening. There is no validated model: real sessions always show "No reliable
 * estimate available". Only synthetic demo sessions (created by scripts.seed_synthetic_demo) can
 * run the hand-set demo formula, and only when the server has SCREENING_MODE=synthetic_demo.
 * Everything shown here is read from the saved result, the same row the PDF report prints.
 */
export function ScreeningPanel({ sessionId }: { sessionId: number }) {
  const view = useApi(() => api.screening(sessionId), [sessionId]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      await api.runScreening(sessionId);
      view.reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRunning(false);
    }
  }

  const v = view.data;
  return (
    <Card className={v?.session_is_synthetic ? "border-warning/60" : undefined}>
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-3 space-y-0">
        <div className="space-y-1.5">
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="size-5 text-primary" /> Experimental screening
          </CardTitle>
          <CardDescription className="max-w-2xl">
            No model has been trained or validated for VisoNarc, because no labelled dataset with independent reference
            outcomes is available. Results here are never a diagnosis or proof of drug use.
          </CardDescription>
        </div>
        {v?.can_run && (
          <Button onClick={run} disabled={running}>
            {running ? <Loader2 className="animate-spin" /> : <Play />} Run demo screening
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <Alert variant="destructive">{error}</Alert>}
        {view.loading && !v ? (
          <LoadingState />
        ) : view.error ? (
          <ErrorState message={view.error} onRetry={view.reload} />
        ) : !v ? null : (
          <>
            {v.session_is_synthetic ? (
              <Alert variant="warning">
                <div className="space-y-1">
                  <p className="font-semibold">SYNTHETIC DEMONSTRATION SESSION</p>
                  <p className="text-sm">
                    Generated from synthetic signals, not a real person. Any score is the output of a hand-set demo
                    formula and is not a probability about anyone.
                  </p>
                </div>
              </Alert>
            ) : (
              <div className="flex items-start gap-3 rounded-lg border bg-muted/30 p-4">
                <ShieldAlert className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
                <div className="space-y-1">
                  <p className="font-medium">No reliable estimate available</p>
                  <p className="text-sm text-muted-foreground">{v.message}</p>
                </div>
              </div>
            )}
            {v.session_is_synthetic && !v.can_run && <p className="text-sm text-muted-foreground">{v.message}</p>}
            {v.results.length > 0 && (
              <ul className="space-y-3">
                {v.results.map((r) => (
                  <ResultRow key={r.id} r={r} />
                ))}
              </ul>
            )}
            {v.session_is_synthetic && v.results.length === 0 && (
              <p className="text-sm text-muted-foreground">No demo screening has been saved for this session yet.</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ResultRow({ r }: { r: ScreeningResult }) {
  const scored = r.estimate !== null;
  return (
    <li className="space-y-3 rounded-lg border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">Screening result #{r.id}</span>
        <Badge variant="warning">Synthetic demo</Badge>
        {!scored && <Badge variant="warning">{r.model_status.replace("_", " ")}</Badge>}
        <span className="text-xs text-muted-foreground">{formatDateTime(r.created_at)}</span>
      </div>
      {scored ? (
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Demo score" value={`${((r.estimate ?? 0) * 100).toFixed(1)} %`} note="hand-set formula, not a probability" />
          <Stat label="Demo label" value={r.classification ?? "-"} note={`synthetic label, threshold ${r.decision_threshold?.toFixed(2)}`} />
          <Stat label="Feature coverage" value={`${Math.round((r.coverage ?? 0) * 100)} %`} note="scored features measured" />
        </div>
      ) : (
        <Alert variant="warning">
          <div className="space-y-1">
            <p className="font-medium">Insufficient evidence: no estimate</p>
            <p className="text-sm">{r.explanation.reasons?.join(" ") || "The inputs did not meet the requirements."}</p>
          </div>
        </Alert>
      )}
      <dl className="grid gap-x-6 gap-y-1 text-xs text-muted-foreground sm:grid-cols-2">
        <div>Model: {r.model_name} {r.model_version}</div>
        <div>Input: combined record #{r.combined_result_id} · schema v{r.feature_schema_version ?? "-"}</div>
        <div>
          Inputs:{" "}
          {Object.entries(r.input_measurement_ids)
            .map(([m, id]) => `${m} #${id}`)
            .join(", ") || "-"}
        </div>
        <div>Missing modalities: {r.missing_modalities.join(", ") || "none"}</div>
      </dl>
      <p className="text-xs text-muted-foreground">Target: {r.target_definition}</p>
    </li>
  );
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-md bg-muted/40 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
      <p className="text-xs text-muted-foreground">{note}</p>
    </div>
  );
}
