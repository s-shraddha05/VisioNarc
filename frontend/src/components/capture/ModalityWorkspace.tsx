import { ChevronDown, Info, Loader2, RefreshCw, Sparkles, Trash2, UploadCloud } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FeatureTable, useFeatureCatalogue } from "@/components/analysis/FeatureTable";
import { PageHeader } from "@/components/common/PageHeader";
import { PrivacyNotice, ResearchNotice, UnavailableNotice } from "@/components/common/Notices";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { SessionPicker } from "@/components/capture/SessionPicker";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/form-controls";
import { useApi } from "@/hooks/useApi";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { analyzeBlockers } from "@/lib/analyzeReadiness";
import { api, errorMessage } from "@/lib/api";
import { formatBytes, formatDateTime } from "@/lib/format";
import type { MediaInfo } from "@/lib/media";
import type { Capabilities, Measurement, Modality, SessionDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface CapturedMedia {
  blob: Blob;
  url: string;
  origin: "upload" | "webcam" | "microphone";
  name: string;
  info: MediaInfo;
}

export type AnalyzeFn = (media: CapturedMedia, sessionId: number, progress: (text: string) => void) => Promise<Measurement>;

const CAPABILITY: Record<Modality, keyof Capabilities> = {
  face: "face_analysis",
  motion: "motion_analysis",
  voice: "voice_analysis",
};

interface Tab {
  id: string;
  label: string;
  icon: ReactNode;
  render: (onMedia: (m: CapturedMedia) => void) => ReactNode;
}

/**
 * Shared layout for the face / motion / voice pages: session + consent check, capture tabs,
 * local preview, analysis, and the session's stored measurements.
 */
export function ModalityWorkspace({
  modality,
  title,
  description,
  tabs,
  renderPreview,
  measurementsOf,
  renderMeasurement,
  onAnalyze,
  dataFlow,
  uploadConfirmation,
}: {
  modality: Modality;
  title: string;
  description: string;
  tabs: Tab[];
  renderPreview: (media: CapturedMedia) => ReactNode;
  measurementsOf: (s: SessionDetail) => Measurement[];
  renderMeasurement: (m: Measurement) => ReactNode;
  onAnalyze: AnalyzeFn;
  /** Plain statement of exactly what leaves the browser when Analyse is pressed. */
  dataFlow: ReactNode;
  /** When set, the user must tick this statement before each upload (used for voice). */
  uploadConfirmation?: string;
}) {
  useDocumentTitle(title);
  useFeatureCatalogue(); // prefetch labels so results render with them immediately
  const [params, setParams] = useSearchParams();
  const sessionId = params.get("session") ? Number(params.get("session")) : null;
  const [tab, setTab] = useState(tabs[0].id);
  const [media, setMedia] = useState<CapturedMedia | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [result, setResult] = useState<Measurement | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  const settings = useApi(api.settings, []);
  const session = useApi(() => (sessionId ? api.getSession(sessionId) : Promise.resolve(null)), [sessionId]);

  // Release the object URL whenever the media is replaced or the page unmounts.
  useEffect(() => () => void (media && URL.revokeObjectURL(media.url)), [media]);
  // A new capture (or session) needs a fresh upload confirmation.
  useEffect(() => {
    setConfirmed(false);
    setAnalyzeError(null);
  }, [media, sessionId]);
  // Never show the previous session's result under a different session.
  useEffect(() => {
    setResult(null);
    setExpanded(null);
  }, [sessionId]);

  const engineReady = settings.data?.capabilities[CAPABILITY[modality]] ?? false;
  const detail = session.data;
  const measurements = detail ? measurementsOf(detail) : [];
  const consentField = ({ face: "allow_face", motion: "allow_motion", voice: "allow_voice" } as const)[modality];
  const sessionProblem = !detail
    ? null
    : detail.consent_withdrawn
      ? "Consent was withdrawn for this session. No further captures are allowed."
      : !detail[consentField]
        ? `The consent recorded for this session does not cover ${modality} capture.`
        : !["consented", "in_progress"].includes(detail.status)
          ? `This session is ${detail.status.replace("_", " ")} and no longer accepts captures.`
          : null;
  const busy = progress !== null;
  const blockers = analyzeBlockers({
    modality,
    capabilitiesState: settings.data ? "ready" : settings.error ? "error" : "loading",
    engineAvailable: engineReady,
    sessionSelected: !!sessionId,
    sessionProblem,
    hasMedia: !!media,
    needsConfirmation: !!uploadConfirmation,
    confirmed,
    busy,
  });
  const canAnalyze = !busy && blockers.length === 0;

  function selectSession(id: number | null) {
    const next = new URLSearchParams(params);
    if (id) next.set("session", String(id));
    else next.delete("session");
    setParams(next, { replace: true });
  }

  async function analyze() {
    if (!media || !sessionId) return;
    setAnalyzeError(null);
    setResult(null);
    setProgress("Starting…");
    // Development-only trace; never logs media content or feature values.
    if (import.meta.env.DEV) console.info(`[VisoNarc] ${modality} analysis started`, { sessionId, bytes: media.blob.size });
    try {
      const measurement = await onAnalyze(media, sessionId, setProgress);
      setResult(measurement);
      setConfirmed(false);
      session.reload();
    } catch (err) {
      setAnalyzeError(errorMessage(err));
    } finally {
      setProgress(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Analysis" title={title} description={description} />
      <ResearchNotice />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>1 · Session and consent</CardTitle>
              <CardDescription>Captures are only allowed for sessions whose recorded consent covers {modality}.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <SessionPicker modality={modality} value={sessionId} onChange={selectSession} />
              {sessionProblem && <Alert variant="destructive">{sessionProblem}</Alert>}
              {session.error && <Alert variant="destructive">{session.error}</Alert>}
              {detail?.consent && (
                <p className="text-xs text-muted-foreground">
                  Consent v{detail.consent.consent_text_version} given by “{detail.consent.consented_by_label}” on{" "}
                  {formatDateTime(detail.consent.consented_at)}.{" "}
                  <Link className="text-primary hover:underline" to={`/history/${detail.id}`}>
                    View session
                  </Link>
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>2 · Capture or upload</CardTitle>
              <CardDescription>The capture stays in this browser tab until you press Analyse.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div role="tablist" aria-label="Capture method" className="inline-flex rounded-lg bg-muted p-1">
                {tabs.map((t) => (
                  <button
                    key={t.id}
                    role="tab"
                    aria-selected={tab === t.id}
                    onClick={() => setTab(t.id)}
                    className={cn(
                      "inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [&_svg]:size-4",
                      tab === t.id ? "bg-card shadow-sm" : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {t.icon}
                    {t.label}
                  </button>
                ))}
              </div>
              <div role="tabpanel">{tabs.find((t) => t.id === tab)?.render(setMedia)}</div>
              <PrivacyNotice>{dataFlow}</PrivacyNotice>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>3 · Preview</CardTitle>
              <CardDescription>Check quality before analysis.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {media ? (
                <>
                  {renderPreview(media)}
                  <dl className="grid grid-cols-2 gap-2 text-xs">
                    <dt className="text-muted-foreground">Source</dt>
                    <dd className="text-right capitalize">{media.origin}</dd>
                    <dt className="text-muted-foreground">Size</dt>
                    <dd className="text-right">{formatBytes(media.blob.size)}</dd>
                    {media.info.width !== undefined && (
                      <>
                        <dt className="text-muted-foreground">Resolution</dt>
                        <dd className="text-right">
                          {media.info.width}×{media.info.height}
                        </dd>
                      </>
                    )}
                    {media.info.durationSeconds !== undefined && Number.isFinite(media.info.durationSeconds) && (
                      <>
                        <dt className="text-muted-foreground">Duration</dt>
                        <dd className="text-right">{media.info.durationSeconds.toFixed(1)} s</dd>
                      </>
                    )}
                  </dl>
                  <Button variant="outline" className="w-full" onClick={() => setMedia(null)} disabled={busy}>
                    <Trash2 /> Discard
                  </Button>
                </>
              ) : (
                <EmptyState icon={Info} title="Nothing captured yet" description="Upload a file or use the device on the left." className="py-8" />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>4 · Analyse</CardTitle>
              <CardDescription>Produces measurements only — no score, label or diagnosis.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {uploadConfirmation && media && (
                <label className="flex items-start gap-3 rounded-lg border border-warning/50 bg-warning/10 p-3 text-sm">
                  <Checkbox className="mt-0.5" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} disabled={busy} />
                  <span>
                    <UploadCloud className="mr-1 inline size-4 align-text-bottom" />
                    {uploadConfirmation}
                  </span>
                </label>
              )}
              <Button
                className="w-full"
                disabled={!canAnalyze}
                aria-describedby={blockers.length ? "analyze-blockers" : undefined}
                onClick={() => void analyze()}
              >
                {busy ? <Loader2 className="animate-spin" /> : <Sparkles />}
                {busy ? progress : `Run ${modality} analysis`}
              </Button>
              {blockers.length > 0 && (
                <div id="analyze-blockers" role="status" aria-live="polite" className="space-y-1 text-xs text-muted-foreground">
                  <p className="font-medium text-foreground">Not ready yet:</p>
                  <ul className="list-disc space-y-0.5 pl-4">
                    {blockers.map((b) => (
                      <li key={b}>{b}</li>
                    ))}
                  </ul>
                </div>
              )}
              {settings.data && !engineReady && (
                <UnavailableNotice title="Analysis not available on this server">
                  The server reports that {modality} analysis is not installed (NumPy missing). See README → Phase 3 setup.
                </UnavailableNotice>
              )}
              {analyzeError && <Alert variant="destructive">{analyzeError}</Alert>}
              {settings.error && (
                <Alert variant="destructive" className="flex-col gap-2">
                  <span>{settings.error}</span>
                  <Button variant="outline" size="sm" className="self-start" onClick={settings.reload}>
                    <RefreshCw /> Retry
                  </Button>
                </Alert>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {result && (
        <Card className="border-primary/40">
          <CardHeader className="flex-row flex-wrap items-center justify-between gap-2 space-y-0">
            <div className="space-y-1.5">
              <CardTitle>New {modality} measurement</CardTitle>
              <CardDescription>
                Saved {formatDateTime(result.captured_at)} · quality{" "}
                {result.quality_score === null ? "n/a" : `${Math.round(result.quality_score * 100)} %`} (engineering check, not a
                confidence value) · {result.extractor_version}
              </CardDescription>
            </div>
            <Badge variant={result.is_reliable ? "success" : "warning"}>
              {result.is_reliable ? "Passed quality checks" : "Failed a quality check"}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            {result.warnings.length > 0 && (
              <Alert variant="warning">
                <ul className="list-disc space-y-0.5 pl-4">
                  {result.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </Alert>
            )}
            <FeatureTable modality={modality} measurement={result} />
            {sessionId && (
              <Button asChild variant="outline" size="sm">
                <Link to={`/analysis/combined?session=${sessionId}`}>Open multimodal summary</Link>
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Stored {modality} measurements</CardTitle>
          <CardDescription>Records for the selected session, read from the database.</CardDescription>
        </CardHeader>
        <CardContent>
          {!sessionId ? (
            <EmptyState title="No session selected" description="Select a session to see its measurements." className="py-8" />
          ) : session.loading && !detail ? (
            <LoadingState />
          ) : session.error ? (
            <ErrorState message={session.error} onRetry={session.reload} />
          ) : measurements.length === 0 ? (
            <EmptyState title="No measurements yet" description="Run an analysis to create the first one." className="py-8" />
          ) : (
            <ul className="divide-y">
              {[...measurements].reverse().map((m) => (
                <li key={m.id} className="py-3">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="text-sm">
                      <p className="font-medium">{formatDateTime(m.captured_at)}</p>
                      <p className="text-xs text-muted-foreground">
                        {m.source} · schema {m.feature_schema_version} · {m.extractor_version ?? "extractor version not recorded"}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {renderMeasurement(m)}
                      <Badge variant={m.is_reliable ? "success" : "warning"}>{m.is_reliable ? "Reliable" : "Low quality"}</Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-expanded={expanded === m.id}
                        onClick={() => setExpanded((v) => (v === m.id ? null : m.id))}
                      >
                        Details <ChevronDown className={cn("transition-transform", expanded === m.id && "rotate-180")} />
                      </Button>
                    </div>
                  </div>
                  {expanded === m.id && (
                    <div className="mt-3 space-y-3 rounded-lg bg-muted/40 p-3">
                      {m.warnings.length > 0 && (
                        <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted-foreground">
                          {m.warnings.map((w) => (
                            <li key={w}>{w}</li>
                          ))}
                        </ul>
                      )}
                      <FeatureTable modality={modality} measurement={m} />
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
