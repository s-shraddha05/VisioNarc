import {
  Activity,
  AlertTriangle,
  AudioLines,
  BookOpen,
  CheckCircle2,
  CircleDashed,
  Flag,
  ScanFace,
  XCircle,
} from "lucide-react";
import { useId, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ProvenanceBadge, formatFeatureValue } from "@/components/analysis/FeatureTable";
import { IntegrationRecords } from "@/components/analysis/IntegrationRecords";
import { ScreeningPanel } from "@/components/analysis/ScreeningPanel";
import { PageHeader } from "@/components/common/PageHeader";
import { ResearchNotice } from "@/components/common/Notices";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Select } from "@/components/ui/form-controls";
import { Label } from "@/components/ui/label";
import { useApi } from "@/hooks/useApi";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { ModalitySummary } from "@/lib/types";
import { cn } from "@/lib/utils";

const ICONS = { face: ScanFace, motion: Activity, voice: AudioLines };

const STATUS_UI: Record<ModalitySummary["status"], { label: string; icon: typeof CheckCircle2; className: string }> = {
  available: { label: "Measured, passed quality checks", icon: CheckCircle2, className: "text-success" },
  low_quality: { label: "Measured, failed a quality check", icon: AlertTriangle, className: "text-[oklch(0.55_0.12_70)]" },
  missing: { label: "Not captured — excluded", icon: CircleDashed, className: "text-muted-foreground" },
  not_consented: { label: "Not consented — excluded", icon: XCircle, className: "text-muted-foreground" },
  consent_withdrawn: { label: "Consent withdrawn", icon: XCircle, className: "text-destructive" },
};

export function MultimodalPage() {
  useDocumentTitle("Multimodal summary");
  const selectId = useId();
  const [params, setParams] = useSearchParams();
  const sessionId = params.get("session") ? Number(params.get("session")) : null;
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [completeError, setCompleteError] = useState<string | null>(null);

  const sessions = useApi(
    () => api.listSessions({ status: ["consented", "in_progress", "completed"], page: 1, page_size: 100 }),
    [],
  );
  const summary = useApi(() => (sessionId ? api.multimodalSummary(sessionId) : Promise.resolve(null)), [sessionId]);
  const s = summary.data;
  const canComplete =
    !!s && ["consented", "in_progress"].includes(s.session_status) && s.modalities.some((m) => m.measurement_count > 0);

  async function complete() {
    if (!sessionId) return;
    setCompleting(true);
    setCompleteError(null);
    try {
      await api.completeSession(sessionId);
      setConfirmOpen(false);
      summary.reload();
      sessions.reload();
    } catch (err) {
      setCompleteError(errorMessage(err));
    } finally {
      setCompleting(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Analysis"
        title="Multimodal summary"
        description="Shows the measured face, motion and voice features of a session side by side, with data quality and the modalities that are missing. VisoNarc deliberately does not combine them into a score, probability or classification."
      />
      <ResearchNotice />

      <Card>
        <CardHeader>
          <CardTitle>Session</CardTitle>
        </CardHeader>
        <CardContent>
          {sessions.loading && !sessions.data ? (
            <LoadingState />
          ) : sessions.error ? (
            <ErrorState message={sessions.error} onRetry={sessions.reload} />
          ) : !sessions.data?.items.length ? (
            <EmptyState
              title="No eligible sessions"
              description="Create a session and capture at least one modality first."
              action={
                <Button asChild size="sm">
                  <Link to="/analysis/new">New analysis</Link>
                </Button>
              }
              className="py-8"
            />
          ) : (
            <div className="max-w-xl space-y-2">
              <Label htmlFor={selectId}>Analysis session</Label>
              <Select
                id={selectId}
                value={sessionId ?? ""}
                onChange={(e) => {
                  const next = new URLSearchParams(params);
                  if (e.target.value) next.set("session", e.target.value);
                  else next.delete("session");
                  setParams(next, { replace: true });
                }}
              >
                <option value="">Select a session…</option>
                {sessions.data.items.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.reference_code} · {x.subject_label}
                  </option>
                ))}
              </Select>
            </div>
          )}
        </CardContent>
      </Card>

      {sessionId &&
        (summary.loading && !s ? (
          <LoadingState label="Building summary…" />
        ) : summary.error ? (
          <ErrorState message={summary.error} onRetry={summary.reload} />
        ) : s ? (
          <>
            <Card>
              <CardContent className="flex flex-col gap-4 pt-6 lg:flex-row lg:items-center lg:justify-between">
                <div className="space-y-1">
                  <p className="flex flex-wrap items-center gap-2 font-medium">
                    <span className="font-mono text-sm">{s.reference_code}</span> <StatusBadge status={s.session_status} />
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Measured: {s.available_modalities.join(", ") || "none"} · Excluded: {s.missing_modalities.join(", ") || "none"} ·
                    feature schema v{s.feature_schema_version} · generated {formatDateTime(s.generated_at)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button asChild variant="outline">
                    <Link to={`/history/${s.session_id}`}>Session record</Link>
                  </Button>
                  <Button onClick={() => setConfirmOpen(true)} disabled={!canComplete} title={canComplete ? undefined : "Needs an active session with at least one measurement"}>
                    <Flag /> Mark session complete
                  </Button>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-6 xl:grid-cols-3">
              {s.modalities.map((m) => (
                <ModalityCard key={m.modality} m={m} sessionId={s.session_id} active={["consented", "in_progress"].includes(s.session_status)} />
              ))}
            </div>

            <IntegrationRecords
              key={s.session_id}
              sessionId={s.session_id}
              canCreate={["consented", "in_progress", "completed"].includes(s.session_status)}
            />

            <ScreeningPanel key={`screening-${s.session_id}`} sessionId={s.session_id} />

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="size-5 text-[oklch(0.55_0.12_70)]" /> Limitations
                </CardTitle>
                <CardDescription>Read these before interpreting any value above.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="list-disc space-y-1.5 pl-5 text-sm">
                  {s.limitations.map((l) => (
                    <li key={l}>{l}</li>
                  ))}
                </ul>
                <div className="space-y-1.5">
                  <p className="flex items-center gap-2 text-sm font-medium">
                    <BookOpen className="size-4" /> Method sources (how values are computed, not reference values)
                  </p>
                  <ul className="space-y-1 text-xs text-muted-foreground">
                    {Object.entries(s.method_sources).map(([k, v]) => (
                      <li key={k}>{v}</li>
                    ))}
                  </ul>
                </div>
              </CardContent>
            </Card>
          </>
        ) : null)}

      <ConfirmDialog
        open={confirmOpen}
        title="Mark this session complete?"
        description="No further captures will be accepted for this session. Stored measurements are kept until the retention date."
        confirmLabel="Mark complete"
        busy={completing}
        error={completeError}
        onConfirm={complete}
        onCancel={() => {
          setConfirmOpen(false);
          setCompleteError(null);
        }}
      />
    </div>
  );
}

function ModalityCard({ m, sessionId, active }: { m: ModalitySummary; sessionId: number; active: boolean }) {
  const Icon = ICONS[m.modality];
  const ui = STATUS_UI[m.status];
  const measured = m.status === "available" || m.status === "low_quality";
  return (
    <Card className={cn(!measured && "bg-muted/30")}>
      <CardHeader className="space-y-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 capitalize">
            <span className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Icon className="size-5" />
            </span>
            {m.modality}
          </CardTitle>
          <Badge variant="neutral">{m.measurement_count} stored</Badge>
        </div>
        <p className={cn("flex items-center gap-1.5 text-sm font-medium", ui.className)}>
          <ui.icon className="size-4" /> {ui.label}
        </p>
        <CardDescription>{m.status_reason}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {measured ? (
          <>
            <p className="text-xs text-muted-foreground">
              {formatDateTime(m.captured_at)} · {m.source} · quality {m.quality_score === null ? "n/a" : `${Math.round(m.quality_score * 100)} %`}
            </p>
            <dl className="divide-y text-sm">
              {m.key_features.map((f) => (
                <div key={f.key} className="flex items-start justify-between gap-3 py-2">
                  <dt className="space-y-1">
                    <span className="block">{f.label}</span>
                    <ProvenanceBadge provenance={f.provenance} title={f.provenance_label} />
                  </dt>
                  <dd className="text-right font-medium tabular-nums">{formatFeatureValue(f.value, f.unit)}</dd>
                </div>
              ))}
            </dl>
            {m.warnings.length > 0 && (
              <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted-foreground">
                {m.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            )}
          </>
        ) : null}
        {active && (m.status === "missing" || m.status === "low_quality") && (
          <Button asChild variant="outline" size="sm" className="w-full">
            <Link to={`/analysis/${m.modality}?session=${sessionId}`}>
              {m.status === "missing" ? "Capture" : "Capture again"} {m.modality}
            </Link>
          </Button>
        )}
        {m.status === "low_quality" && (
          <Alert variant="warning" className="text-xs">
            Values that failed a quality check are shown for transparency only.
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
