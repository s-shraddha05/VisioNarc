import { ChevronDown, ClipboardList, X } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/common/PageHeader";
import { Pagination } from "@/components/common/Pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/form-controls";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApi } from "@/hooks/useApi";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api } from "@/lib/api";
import { describeAction, formatDateTime } from "@/lib/format";
import type { AuditEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 25;

function variantFor(action: string): BadgeVariant {
  if (action.endsWith("failed") || action.endsWith("locked") || action.endsWith("deleted")) return "destructive";
  if (action.startsWith("auth.")) return "neutral";
  if (action.endsWith("withdrawn")) return "warning";
  return "default";
}

export function AuditPage() {
  useDocumentTitle("Audit activity");
  const [params, setParams] = useSearchParams();
  const action = params.get("action") || undefined;
  const from = params.get("from") || undefined;
  const to = params.get("to") || undefined;
  const page = Math.max(1, Number(params.get("page")) || 1);

  const actions = useApi(api.auditActions, []);
  const logs = useApi(
    () => api.auditLogs({ page, page_size: PAGE_SIZE, action, date_from: from, date_to: to }),
    [page, action, from, to],
  );

  function set(changes: Record<string, string | undefined>, keepPage = false) {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(changes)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    if (!keepPage) next.delete("page");
    setParams(next, { replace: true });
  }

  const groups = Array.from(new Set((actions.data ?? []).map((a) => a.split(".")[0])));
  const filtered = !!(action || from || to);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Records"
        title="Audit activity"
        description="Security and data events recorded by the server: sign-ins, consent, exports and deletions. Entries cannot be edited from the UI."
      />

      <Card>
        <CardContent className="grid gap-3 pt-6 sm:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_1fr_1fr_auto] lg:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="a-action">Event type</Label>
            <Select id="a-action" value={action ?? ""} onChange={(e) => set({ action: e.target.value || undefined })}>
              <option value="">All events</option>
              {groups.map((g) => (
                <optgroup key={g} label={g}>
                  <option value={g}>All {g} events</option>
                  {(actions.data ?? [])
                    .filter((a) => a.startsWith(`${g}.`))
                    .map((a) => (
                      <option key={a} value={a}>
                        {describeAction(a)}
                      </option>
                    ))}
                </optgroup>
              ))}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="a-from">From</Label>
            <Input id="a-from" type="date" value={from ?? ""} onChange={(e) => set({ from: e.target.value || undefined })} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="a-to">To</Label>
            <Input id="a-to" type="date" value={to ?? ""} onChange={(e) => set({ to: e.target.value || undefined })} />
          </div>
          <Button variant="ghost" disabled={!filtered} onClick={() => setParams(new URLSearchParams(), { replace: true })}>
            <X /> Clear
          </Button>
        </CardContent>
      </Card>

      {logs.error ? (
        <ErrorState message={logs.error} onRetry={logs.reload} />
      ) : !logs.data ? (
        <LoadingState />
      ) : logs.data.total === 0 ? (
        <EmptyState icon={ClipboardList} title={filtered ? "No events match these filters" : "No audit events yet"} />
      ) : (
        <Card className={logs.loading ? "opacity-60 transition-opacity" : undefined}>
          <ul className="divide-y">
            {logs.data.items.map((e) => (
              <AuditRow key={e.id} event={e} />
            ))}
          </ul>
          <div className="border-t p-4">
            <Pagination page={page} pageSize={PAGE_SIZE} total={logs.data.total} onPage={(p) => set({ page: p > 1 ? String(p) : undefined }, true)} />
          </div>
        </Card>
      )}
    </div>
  );
}

function AuditRow({ event: e }: { event: AuditEvent }) {
  const [open, setOpen] = useState(false);
  const hasDetails = !!e.details && Object.keys(e.details).length > 0;
  return (
    <li className="p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{describeAction(e.action)}</span>
            <Badge variant={variantFor(e.action)} className="font-mono">
              {e.action}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            {formatDateTime(e.created_at)} · {e.admin_username ?? "no administrator"}
            {e.ip_address && ` · ${e.ip_address}`}
            {e.entity_type && ` · ${e.entity_type} #${e.entity_id}`}
          </p>
        </div>
        {hasDetails && (
          <Button variant="ghost" size="sm" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
            Details <ChevronDown className={cn("transition-transform", open && "rotate-180")} />
          </Button>
        )}
      </div>
      {open && hasDetails && (
        <pre className="mt-3 overflow-x-auto rounded-lg bg-muted p-3 text-xs">{JSON.stringify(e.details, null, 2)}</pre>
      )}
    </li>
  );
}
