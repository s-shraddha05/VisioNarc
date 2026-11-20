import { FileJson, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/common/PageHeader";
import { UnavailableNotice } from "@/components/common/Notices";
import { Pagination } from "@/components/common/Pagination";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { SessionFilterBar, useSessionFilters } from "@/components/sessions/SessionFilterBar";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useApi } from "@/hooks/useApi";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const PAGE_SIZE = 10;

export function ReportsPage() {
  useDocumentTitle("Reports");
  const filterState = useSessionFilters();
  const { filters, page, setPage } = filterState;
  const list = useApi(() => api.listSessions({ ...filters, page, page_size: PAGE_SIZE }), [JSON.stringify(filters), page]);
  const settings = useApi(api.settings, []);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  async function run(key: string, fn: () => Promise<string>) {
    setBusy(key);
    setError(null);
    setSaved(null);
    try {
      setSaved(await fn());
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Records"
        title="Reports & export"
        description="Download real session data. Every export carries the VisoNarc name and the research disclaimer, and is recorded in the audit log."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <FileSpreadsheet className="size-5 text-primary" />
            <CardTitle>Session list (CSV)</CardTitle>
            <CardDescription>All sessions matching the filters below, up to 5,000 rows.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" onClick={() => run("csv", () => api.downloadSessionsCsv(filters))} disabled={!!busy || !list.data?.total}>
              {busy === "csv" ? <Loader2 className="animate-spin" /> : <FileSpreadsheet />} Download CSV
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <FileJson className="size-5 text-primary" />
            <CardTitle>Session record (JSON)</CardTitle>
            <CardDescription>Full record of one session: consent, measurements and results.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Use the download button on a session in the list below.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <FileText className="size-5 text-primary" />
            <CardTitle>Session report (PDF)</CardTitle>
            <CardDescription>
              Server-generated report: session, consent, measurements with quality warnings, saved combined records,
              provenance and limitations. No raw media, no score.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {settings.data && !settings.data.capabilities.pdf_reports ? (
              <UnavailableNotice title="Not available on this server">
                ReportLab is not installed in the backend environment (see README).
              </UnavailableNotice>
            ) : (
              <p className="text-sm text-muted-foreground">Use the PDF button on a session in the list below.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {error && <Alert variant="destructive">{error}</Alert>}
      {saved && <Alert>Saved {saved} to your downloads.</Alert>}

      <Card>
        <CardContent className="pt-6">
          <SessionFilterBar state={filterState} />
        </CardContent>
      </Card>

      {list.error ? (
        <ErrorState message={list.error} onRetry={list.reload} />
      ) : !list.data ? (
        <LoadingState />
      ) : list.data.total === 0 ? (
        <EmptyState title="No sessions to report on" description={filterState.active ? "Try clearing the filters." : "Create an analysis session first."} />
      ) : (
        <Card>
          <ul className="divide-y">
            {list.data.items.map((s) => (
              <li key={s.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link to={`/history/${s.id}`} className="font-medium hover:text-primary">
                      {s.subject_label}
                    </Link>
                    <StatusBadge status={s.status} />
                  </div>
                  <p className="font-mono text-xs text-muted-foreground">
                    {s.reference_code} · {formatDateTime(s.created_at)} · {s.counts.face + s.counts.motion + s.counts.voice} measurements ·{" "}
                    {s.counts.results} results
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => run(`pdf-${s.id}`, () => api.downloadSessionPdf(s.id, s.reference_code))}
                    disabled={!!busy || !settings.data?.capabilities.pdf_reports}
                  >
                    {busy === `pdf-${s.id}` ? <Loader2 className="animate-spin" /> : <FileText />} PDF report
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => run(`json-${s.id}`, () => api.downloadSessionJson(s.id, s.reference_code))}
                    disabled={!!busy}
                  >
                    {busy === `json-${s.id}` ? <Loader2 className="animate-spin" /> : <FileJson />} JSON record
                  </Button>
                </div>
              </li>
            ))}
          </ul>
          <div className="border-t p-4">
            <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPage={setPage} />
          </div>
        </Card>
      )}
    </div>
  );
}
