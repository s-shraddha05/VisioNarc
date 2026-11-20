import {
  Activity,
  ArrowLeft,
  AudioLines,
  CheckCircle2,
  ChevronDown,
  Download,
  FileText,
  Layers,
  Loader2,
  ScanFace,
  ShieldOff,
  Trash2,
  XCircle,
} from "lucide-react";
import { Fragment, useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { FeatureTable } from "@/components/analysis/FeatureTable";
import { PageHeader } from "@/components/common/PageHeader";
import { ResearchNotice } from "@/components/common/Notices";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useApi } from "@/hooks/useApi";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, errorMessage } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";
import type { Measurement, Modality, SessionDetail } from "@/lib/types";
import { cn } from "@/lib/utils";
import { NotFoundPage } from "@/pages/NotFoundPage";

type Dialog = "withdraw" | "delete" | null;

export function SessionDetailPage() {
  const { id } = useParams();
  const sessionId = Number(id);
  const valid = Number.isInteger(sessionId) && sessionId > 0;
  const navigate = useNavigate();
  const location = useLocation();
  // Show the "created" banner once; clear router state so a reload does not show it again.
  const [justCreated] = useState(() => !!(location.state as { created?: boolean } | null)?.created);
  useEffect(() => {
    if (location.state) navigate(location.pathname, { replace: true, state: null });
  }, [location.state, location.pathname, navigate]);

  const session = useApi(() => (valid ? api.getSession(sessionId) : Promise.reject(new Error("invalid"))), [sessionId]);
  useDocumentTitle(session.data ? session.data.reference_code : "Session");

  const [dialog, setDialog] = useState<Dialog>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<"json" | "pdf" | null>(null);
  const [toDelete, setToDelete] = useState<{ modality: Modality; m: Measurement } | null>(null);

  if (!valid || session.error === "Analysis session not found.") return <NotFoundPage what="analysis session" />;
  if (session.error) return <ErrorState message={session.error} onRetry={session.reload} />;
  if (!session.data) return <LoadingState label="Loading session…" />;

  const s = session.data;
  const active = (s.status === "consented" || s.status === "in_progress") && !s.consent_withdrawn;

  async function runAction() {
    setBusy(true);
    setActionError(null);
    try {
      if (dialog === "withdraw") {
        await api.withdrawConsent(s.id);
        setDialog(null);
        session.reload();
      } else if (dialog === "delete") {
        await api.deleteSession(s.id);
        navigate("/history", { replace: true });
        return;
      }
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function askDelete(modality: Modality, m: Measurement) {
    setActionError(null);
    setToDelete({ modality, m });
  }

  const dependentRecords = toDelete
    ? s.combined_results.filter((r) =>
        (r.source_measurements ?? []).some((x) => x.modality === toDelete.modality && x.measurement_id === toDelete.m.id),
      ).length
    : 0;

  async function deleteMeasurement() {
    if (!toDelete) return;
    setBusy(true);
    setActionError(null);
    try {
      await api.deleteMeasurement(s.id, toDelete.modality, toDelete.m.id);
      setToDelete(null);
      session.reload();
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function download(kind: "json" | "pdf") {
    setDownloading(kind);
    setDownloadError(null);
    try {
      if (kind === "pdf") await api.downloadSessionPdf(s.id, s.reference_code);
      else await api.downloadSessionJson(s.id, s.reference_code);
    } catch (err) {
      setDownloadError(errorMessage(err));
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2">
        <Link to="/history">
          <ArrowLeft /> Analysis history
        </Link>
      </Button>

      <PageHeader
        eyebrow={<span className="font-mono normal-case tracking-normal">{s.reference_code}</span>}
        title={
          <span className="flex flex-wrap items-center gap-3">
            {s.subject_label} <StatusBadge status={s.status} />
            {s.is_synthetic && <Badge variant="warning">Synthetic demo</Badge>}
          </span>
        }
        description={`Created ${formatDateTime(s.created_at)} by ${s.created_by ?? "a deleted administrator"}`}
        actions={
          <>
            <Button variant="outline" onClick={() => download("pdf")} disabled={!!downloading}>
              {downloading === "pdf" ? <Loader2 className="animate-spin" /> : <FileText />} PDF report
            </Button>
            <Button variant="outline" onClick={() => download("json")} disabled={!!downloading}>
              {downloading === "json" ? <Loader2 className="animate-spin" /> : <Download />} JSON record
            </Button>
            {!s.consent_withdrawn && (
              <Button variant="outline" onClick={() => setDialog("withdraw")}>
                <ShieldOff /> Withdraw consent
              </Button>
            )}
            <Button variant="destructive" onClick={() => setDialog("delete")}>
              <Trash2 /> Delete
            </Button>
          </>
        }
      />

      {justCreated && (
        <Alert>
          <CheckCircle2 className="text-success" />
          <span>Session created and consent recorded. Choose a modality below to start capturing.</span>
        </Alert>
      )}
      {downloadError && <Alert variant="destructive">{downloadError}</Alert>}
      {s.consent_withdrawn && (
        <Alert variant="warning">
          <ShieldOff />
          <span>
            Consent was withdrawn on {formatDateTime(s.consent?.withdrawn_at)}. All measurements and results were deleted;
            the session is kept only as a record of the withdrawal.
          </span>
        </Alert>
      )}

      <ResearchNotice />

      <div className="grid gap-6 md:grid-cols-2 2xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Session</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="divide-y text-sm">
              <Row k="Reference" v={<span className="font-mono text-xs">{s.reference_code}</span>} />
              <Row k="Status" v={<StatusBadge status={s.status} />} />
              <Row k="Created" v={formatDateTime(s.created_at)} />
              <Row k="Last updated" v={formatDateTime(s.updated_at)} />
              <Row k="Completed" v={formatDateTime(s.completed_at)} />
              <Row k="Retain until" v={formatDate(s.retain_until)} />
            </dl>
            {s.notes && (
              <div className="mt-4 rounded-lg bg-muted/50 p-3 text-sm">
                <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Notes</p>
                <p className="whitespace-pre-wrap">{s.notes}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Consent</CardTitle>
            <CardDescription>Text version {s.consent?.consent_text_version ?? "—"}</CardDescription>
          </CardHeader>
          <CardContent>
            {s.consent ? (
              <dl className="divide-y text-sm">
                <Row k="Given by" v={s.consent.consented_by_label} />
                <Row k="Recorded" v={formatDateTime(s.consent.consented_at)} />
                <Row k="Face" v={<YesNo ok={s.consent.allow_face} />} />
                <Row k="Motion" v={<YesNo ok={s.consent.allow_motion} />} />
                <Row k="Voice" v={<YesNo ok={s.consent.allow_voice} />} />
                <Row k="Raw media storage" v={<YesNo ok={s.consent.allow_raw_media_storage} />} />
                <Row k="Withdrawn" v={s.consent.withdrawn_at ? formatDateTime(s.consent.withdrawn_at) : "No"} />
              </dl>
            ) : (
              <EmptyState title="No consent record" className="py-6" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Capture</CardTitle>
            <CardDescription>{active ? "Open a capture page for this session." : "This session no longer accepts captures."}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <CaptureLink to="face" icon={<ScanFace />} label="Face analysis" enabled={active && s.allow_face} id={s.id} />
            <CaptureLink to="motion" icon={<Activity />} label="Motion analysis" enabled={active && s.allow_motion} id={s.id} />
            <CaptureLink to="voice" icon={<AudioLines />} label="Voice analysis" enabled={active && s.allow_voice} id={s.id} />
            <CaptureLink to="combined" icon={<Layers />} label="Multimodal analysis" enabled={active} id={s.id} />
          </CardContent>
        </Card>
      </div>

      <SummaryCard session={s} />
      <MeasurementTable title="Face measurements" modality="face" items={s.facial_measurements} onDelete={askDelete} />
      <MeasurementTable title="Motion measurements" modality="motion" items={s.motion_measurements} onDelete={askDelete} />
      <MeasurementTable title="Voice measurements" modality="voice" items={s.voice_measurements} onDelete={askDelete} />
      <ConfirmDialog
        open={!!toDelete}
        title="Delete this measurement?"
        description={
          toDelete
            ? `${toDelete.modality} measurement #${toDelete.m.id} (${formatDateTime(toDelete.m.captured_at)}) will be permanently deleted` +
              (dependentRecords
                ? `, together with ${dependentRecords} saved combined record(s) that use it.`
                : ". No saved combined record uses it.") +
              " The deletion is recorded in the audit log."
            : ""
        }
        confirmLabel="Delete measurement"
        destructive
        busy={busy}
        error={actionError}
        onConfirm={deleteMeasurement}
        onCancel={() => {
          setToDelete(null);
          setActionError(null);
        }}
      />

      <ConfirmDialog
        open={dialog === "withdraw"}
        title="Withdraw consent?"
        description="This cancels the session and permanently deletes every face, motion and voice measurement and every combined result. The session and consent record are kept to document the withdrawal."
        confirmLabel="Withdraw consent"
        destructive
        busy={busy}
        error={actionError}
        onConfirm={runAction}
        onCancel={() => {
          setDialog(null);
          setActionError(null);
        }}
      />
      <ConfirmDialog
        open={dialog === "delete"}
        title="Delete this session permanently?"
        description="The session, its consent record, all measurements and results are erased. This cannot be undone. The deletion itself is recorded in the audit log."
        confirmLabel="Delete permanently"
        confirmText={s.reference_code}
        destructive
        busy={busy}
        error={actionError}
        onConfirm={runAction}
        onCancel={() => {
          setDialog(null);
          setActionError(null);
        }}
      />
    </div>
  );
}

function Row({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="text-right font-medium">{v}</dd>
    </div>
  );
}

function YesNo({ ok }: { ok: boolean }) {
  return ok ? (
    <span className="inline-flex items-center gap-1 text-success">
      <CheckCircle2 className="size-4" /> Yes
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-muted-foreground">
      <XCircle className="size-4" /> No
    </span>
  );
}

function CaptureLink({ to, icon, label, enabled, id }: { to: string; icon: ReactNode; label: string; enabled: boolean; id: number }) {
  if (!enabled) {
    return (
      <Button variant="outline" className="w-full justify-start" disabled title="Not consented or session inactive">
        {icon} {label}
      </Button>
    );
  }
  return (
    <Button asChild variant="outline" className="w-full justify-start">
      <Link to={`/analysis/${to}?session=${id}`}>
        {icon} {label}
      </Link>
    </Button>
  );
}


function MeasurementTable({
  title,
  modality,
  items,
  onDelete,
}: {
  title: string;
  modality: Modality;
  items: Measurement[];
  onDelete: (modality: Modality, m: Measurement) => void;
}) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <EmptyState title="No measurements" description="Nothing has been measured for this modality." className="py-6" />
        ) : (
          <div className="relative overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2 pr-4 font-medium">Captured</th>
                  <th className="py-2 pr-4 font-medium">Source</th>
                  <th className="py-2 pr-4 font-medium">Quality check</th>
                  <th className="py-2 pr-4 font-medium">Result</th>
                  <th className="py-2 font-medium">
                    <span className="sr-only">Details</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {items.map((m) => (
                  <Fragment key={m.id}>
                    <tr>
                      <td className="whitespace-nowrap py-2 pr-4">{formatDateTime(m.captured_at)}</td>
                      <td className="py-2 pr-4 capitalize">{m.source}</td>
                      <td className="py-2 pr-4 tabular-nums">{m.quality_score === null ? "—" :`${Math.round(m.quality_score * 100)}%`}</td>
                      <td className="py-2 pr-4">
                        <Badge variant={m.is_reliable ? "success" : "warning"}>{m.is_reliable ? "Passed" : "Failed a check"}</Badge>
                      </td>
                      <td className="py-2 text-right">
                        <Button variant="ghost" size="sm" aria-expanded={open === m.id} onClick={() => setOpen((v) => (v === m.id ? null : m.id))}>
                          Details <ChevronDown className={cn("transition-transform", open === m.id && "rotate-180")} />
                        </Button>
                      </td>
                    </tr>
                    {open === m.id && (
                      <tr>
                        <td colSpan={5} className="bg-muted/30 p-3">
                          {m.warnings.length > 0 && (
                            <ul className="mb-3 list-disc space-y-0.5 pl-5 text-xs text-muted-foreground">
                              {m.warnings.map((w) => (
                                <li key={w}>{w}</li>
                              ))}
                            </ul>
                          )}
                          <FeatureTable modality={modality} measurement={m} />
                          <Button variant="outline" size="sm" className="mt-3 text-destructive" onClick={() => onDelete(modality, m)}>
                            <Trash2 /> Delete this measurement
                          </Button>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SummaryCard({ session }: { session: SessionDetail }) {
  const measured = session.counts.face + session.counts.motion + session.counts.voice;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Multimodal summary</CardTitle>
        <CardDescription>
          VisoNarc does not combine modalities into a score, probability or classification.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          {measured
            ? "See all measured features side by side, with data quality, missing modalities and limitations."
            : "No measurements yet. The summary fills in as modalities are captured."}
        </p>
        <Button asChild variant="outline">
          <Link to={`/analysis/combined?session=${session.id}`}>
            <Layers /> Open summary
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}