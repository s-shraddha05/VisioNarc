import { Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/form-controls";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { STATUS_LABELS } from "@/lib/format";
import { SESSION_STATUSES, type SessionFilters, type SessionStatus } from "@/lib/types";

/** Filters live in the URL so they survive reloads and can be shared/bookmarked. */
export function useSessionFilters() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") as SessionStatus | null;
  const filters: SessionFilters = {
    q: params.get("q") || undefined,
    status: status && SESSION_STATUSES.includes(status) ? [status] : undefined,
    date_from: params.get("from") || undefined,
    date_to: params.get("to") || undefined,
  };
  const page = Math.max(1, Number(params.get("page")) || 1);

  function update(changes: Record<string, string | undefined>, resetPage = true) {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(changes)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    if (resetPage) next.delete("page");
    setParams(next, { replace: true });
  }

  return {
    filters,
    page,
    setPage: (p: number) => update({ page: p > 1 ? String(p) : undefined }, false),
    update,
    active: !!(filters.q || filters.status || filters.date_from || filters.date_to),
    clear: () => setParams(new URLSearchParams(), { replace: true }),
  };
}

export function SessionFilterBar({ state }: { state: ReturnType<typeof useSessionFilters> }) {
  const { filters, update, active, clear } = state;
  const [q, setQ] = useState(filters.q ?? "");

  // Debounce free-text search.
  useEffect(() => {
    const id = setTimeout(() => {
      if ((filters.q ?? "") !== q.trim()) update({ q: q.trim() || undefined });
    }, 350);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  useEffect(() => setQ(filters.q ?? ""), [filters.q]);

  const dateError = filters.date_from && filters.date_to && filters.date_from > filters.date_to;

  return (
    <div className="space-y-2">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))_auto] lg:items-end">
        <div className="space-y-1.5 sm:col-span-2 lg:col-span-1">
          <Label htmlFor="f-q">Search</Label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input id="f-q" className="pl-9" placeholder="Reference code or subject label" value={q} onChange={(e) => setQ(e.target.value)} maxLength={100} />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="f-status">Status</Label>
          <Select id="f-status" value={filters.status?.[0] ?? ""} onChange={(e) => update({ status: e.target.value || undefined })}>
            <option value="">All statuses</option>
            {SESSION_STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="f-from">Created from</Label>
          <Input id="f-from" type="date" value={filters.date_from ?? ""} onChange={(e) => update({ from: e.target.value || undefined })} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="f-to">Created to</Label>
          <Input id="f-to" type="date" value={filters.date_to ?? ""} onChange={(e) => update({ to: e.target.value || undefined })} />
        </div>
        <Button variant="ghost" onClick={clear} disabled={!active} className="lg:mb-0.5">
          <X /> Clear
        </Button>
      </div>
      {dateError && <p className="text-xs text-destructive">“Created from” must be on or before “Created to”.</p>}
    </div>
  );
}
