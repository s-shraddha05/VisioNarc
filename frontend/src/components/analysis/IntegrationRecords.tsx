import { ChevronDown, Database, Loader2, Save } from "lucide-react";
import { useState } from "react";
import { ProvenanceBadge, formatFeatureValue } from "@/components/analysis/FeatureTable";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Alert } from "@/components/ui/alert";
import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useApi } from "@/hooks/useApi";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { CombinedResult, IntegrationFeatureStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS: Record<IntegrationFeatureStatus, { label: string; variant: BadgeVariant }> = {
  measured: { label: "Measured", variant: "success" },
  not_measured: { label: "Not measured", variant: "neutral" },
  missing: { label: "Modality missing", variant: "neutral" },
  not_consented: { label: "Not consented", variant: "neutral" },
  excluded_low_quality: { label: "Excluded: failed quality check", variant: "warning" },
};

/**
 * Saved feature-integration records: the session's quality-checked measurements in a fixed,
 * documented order with provenance and versions. They contain no score, label or confidence.
 */
export function IntegrationRecords({ sessionId, canCreate }: { sessionId: number; canCreate: boolean }) {
  const records = useApi(() => api.listIntegrations(sessionId), [sessionId]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const created = await api.createIntegration(sessionId);
      setOpen(created.id);
      records.reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-3 space-y-0">
        <div className="space-y-1.5">
          <CardTitle className="flex items-center gap-2">
            <Database className="size-5 text-primary" /> Saved combined records
          </CardTitle>
          <CardDescription className="max-w-2xl">
            Saves the latest quality-checked measurement of each consented modality, in a fixed feature order, with
            the versions that produced it. Values are copied as measured; nothing is weighted, combined or scored.
          </CardDescription>
        </div>
        <Button onClick={save} disabled={saving || !canCreate} title={canCreate ? undefined : "Session is not eligible"}>
          {saving ? <Loader2 className="animate-spin" /> : <Save />} Save combined record
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <Alert variant="destructive">{error}</Alert>}
        {records.loading && !records.data ? (
          <LoadingState />
        ) : records.error ? (
          <ErrorState message={records.error} onRetry={records.reload} />
        ) : !records.data?.length ? (
          <EmptyState title="No saved records yet" description="Save one after capturing at least one modality that passes its quality checks." className="py-8" />
        ) : (
          <ul className="divide-y rounded-lg border">
            {records.data.map((r) => (
              <RecordRow key={r.id} record={r} open={open === r.id} onToggle={() => setOpen((v) => (v === r.id ? null : r.id))} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function RecordRow({ record: r, open, onToggle }: { record: CombinedResult; open: boolean; onToggle: () => void }) {
  return (
    <li className="p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1 text-sm">
          <p className="flex flex-wrap items-center gap-2 font-medium">
            Record #{r.id}
            <Badge variant={r.processing_status === "complete" ? "success" : "warning"}>
              {r.processing_status === "complete" ? "All consented modalities" : "Partial"}
            </Badge>
          </p>
          <p className="text-xs text-muted-foreground">
            {formatDateTime(r.created_at)} · modalities: {r.modalities_used.join(", ")} ·{" "}
            {r.feature_schema_version === "mixed" ? "mixed feature schemas (see sources)" : `schema v${r.feature_schema_version}`} ·{" "}
            {r.extractor_version}
          </p>
        </div>
        <Button variant="ghost" size="sm" aria-expanded={open} onClick={onToggle}>
          Details <ChevronDown className={cn("transition-transform", open && "rotate-180")} />
        </Button>
      </div>
      {open && (
        <div className="mt-4 space-y-4">
          <div className="relative overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2 pr-3 font-medium">#</th>
                  <th className="py-2 pr-3 font-medium">Feature</th>
                  <th className="py-2 pr-3 font-medium">Value</th>
                  <th className="py-2 pr-3 font-medium">Status</th>
                  <th className="py-2 font-medium">Computed</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(r.features ?? []).map((f) => (
                  <tr key={f.index}>
                    <td className="py-2 pr-3 tabular-nums text-muted-foreground">{f.index}</td>
                    <td className="py-2 pr-3">
                      <span className="capitalize text-muted-foreground">{f.modality}</span> · {f.label}
                    </td>
                    <td className="py-2 pr-3 tabular-nums">{f.value === null ? "—" : formatFeatureValue(f.value, f.unit)}</td>
                    <td className="py-2 pr-3">
                      <Badge variant={STATUS[f.status].variant}>{STATUS[f.status].label}</Badge>
                    </td>
                    <td className="py-2">
                      <ProvenanceBadge provenance={f.provenance} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="space-y-1 text-xs text-muted-foreground">
            <p className="font-medium text-foreground">Inputs</p>
            {(r.source_measurements ?? []).map((s) => (
              <p key={`${s.modality}-${s.measurement_id}`}>
                <span className="capitalize">{s.modality}</span> measurement #{s.measurement_id} · {formatDateTime(s.captured_at)} ·{" "}
                {s.source} · schema v{s.feature_schema_version} · {s.extractor_version ?? "extractor version not recorded"}
              </p>
            ))}
          </div>
        </div>
      )}
    </li>
  );
}
