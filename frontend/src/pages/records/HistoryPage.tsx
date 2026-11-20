import { ChevronRight, Download, FilePlus2, Loader2, SearchX } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader } from "@/components/common/PageHeader";
import { Pagination } from "@/components/common/Pagination";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { ModalityDots } from "@/components/sessions/ModalityDots";
import { SessionFilterBar, useSessionFilters } from "@/components/sessions/SessionFilterBar";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useApi } from "@/hooks/useApi";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const PAGE_SIZE = 15;

export function HistoryPage() {
  useDocumentTitle("Analysis history");
  const navigate = useNavigate();
  const filterState = useSessionFilters();
  const { filters, page, setPage } = filterState;
  const key = JSON.stringify(filters);
  const list = useApi(() => api.listSessions({ ...filters, page, page_size: PAGE_SIZE }), [key, page]);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  async function exportCsv() {
    setExporting(true);
    setExportError(null);
    try {
      await api.downloadSessionsCsv(filters);
    } catch (err) {
      setExportError(errorMessage(err));
    } finally {
      setExporting(false);
    }
  }

  const data = list.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Records"
        title="Analysis history"
        description="Every analysis session stored in the database, newest first."
        actions={
          <>
            <Button variant="outline" onClick={exportCsv} disabled={exporting || !data?.total}>
              {exporting ? <Loader2 className="animate-spin" /> : <Download />} Export CSV
            </Button>
            <Button asChild>
              <Link to="/analysis/new">
                <FilePlus2 /> New analysis
              </Link>
            </Button>
          </>
        }
      />

      <Card>
        <CardContent className="pt-6">
          <SessionFilterBar state={filterState} />
        </CardContent>
      </Card>

      {exportError && <Alert variant="destructive">{exportError}</Alert>}

      {list.error ? (
        <ErrorState message={list.error} onRetry={list.reload} />
      ) : !data ? (
        <LoadingState label="Loading sessions…" />
      ) : data.total === 0 ? (
        filterState.active ? (
          <EmptyState icon={SearchX} title="No sessions match these filters" action={<Button variant="outline" size="sm" onClick={filterState.clear}>Clear filters</Button>} />
        ) : (
          <EmptyState
            title="No analysis sessions yet"
            description="Sessions appear here after you record a participant's consent."
            action={
              <Button asChild size="sm">
                <Link to="/analysis/new">Create a session</Link>
              </Button>
            }
          />
        )
      ) : (
        <Card className={list.loading ? "opacity-60 transition-opacity" : undefined}>
          {/* Desktop table */}
          <div className="relative hidden overflow-x-auto md:block">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">Reference</th>
                  <th className="px-4 py-3 font-medium">Subject</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Modalities</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3 font-medium">
                    <span className="sr-only">Open</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.items.map((s) => (
                  <tr
                    key={s.id}
                    className="cursor-pointer transition-colors hover:bg-muted/40"
                    onClick={() => navigate(`/history/${s.id}`)}
                  >
                    <td className="px-4 py-3 font-mono text-xs">
                      <Link to={`/history/${s.id}`} className="hover:text-primary focus-visible:underline" onClick={(e) => e.stopPropagation()}>
                        {s.reference_code}
                      </Link>
                    </td>
                    <td className="max-w-48 truncate px-4 py-3 font-medium">
                      {s.subject_label}
                      {s.is_synthetic && <Badge variant="warning" className="ml-2">Synthetic demo</Badge>}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={s.status} />
                    </td>
                    <td className="px-4 py-3">
                      <ModalityDots session={s} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-muted-foreground">{formatDateTime(s.created_at)}</td>
                    <td className="px-4 py-3 text-right text-muted-foreground">
                      <ChevronRight className="ml-auto size-4" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <ul className="divide-y md:hidden">
            {data.items.map((s) => (
              <li key={s.id}>
                <Link to={`/history/${s.id}`} className="flex flex-col gap-2 p-4 hover:bg-muted/40">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">
                      {s.subject_label}
                      {s.is_synthetic && <Badge variant="warning" className="ml-2">Synthetic demo</Badge>}
                    </span>
                    <StatusBadge status={s.status} />
                  </div>
                  <span className="font-mono text-xs text-muted-foreground">{s.reference_code}</span>
                  <div className="flex items-center justify-between">
                    <ModalityDots session={s} />
                    <span className="text-xs text-muted-foreground">{formatDateTime(s.created_at)}</span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>

          <div className="border-t p-4">
            <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPage={setPage} />
          </div>
        </Card>
      )}
    </div>
  );
}
