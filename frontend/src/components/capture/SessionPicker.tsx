import { FilePlus2 } from "lucide-react";
import { useId } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/form-controls";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/States";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import type { Modality, SessionSummary } from "@/lib/types";

const CONSENT_FIELD: Record<Modality, keyof SessionSummary> = {
  face: "allow_face",
  motion: "allow_motion",
  voice: "allow_voice",
};

/** Lists active sessions whose consent covers `modality`. Sessions without that consent are not offered. */
export function SessionPicker({
  modality,
  value,
  onChange,
}: {
  modality: Modality;
  value: number | null;
  onChange: (id: number | null) => void;
}) {
  const id = useId();
  const { data, error, loading, reload } = useApi(
    () => api.listSessions({ status: ["consented", "in_progress"], page: 1, page_size: 100 }),
    [],
  );

  if (loading) return <Skeleton className="h-16 w-full" />;
  if (error) return <ErrorState message={error} onRetry={reload} className="py-6" />;

  const eligible = (data?.items ?? []).filter((s) => s[CONSENT_FIELD[modality]]);
  const skipped = (data?.items.length ?? 0) - eligible.length;

  if (eligible.length === 0) {
    return (
      <div className="flex flex-col gap-3 rounded-lg border border-dashed p-4 text-sm sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted-foreground">
          No active session has <strong>{modality}</strong> consent. Create a session and record consent first.
        </p>
        <Button asChild size="sm">
          <Link to="/analysis/new">
            <FilePlus2 /> New analysis
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>Analysis session</Label>
      <Select id={id} value={value ?? ""} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
        <option value="">Select a session…</option>
        {eligible.map((s) => (
          <option key={s.id} value={s.id}>
            {s.reference_code} · {s.subject_label}
          </option>
        ))}
      </Select>
      {skipped > 0 && (
        <p className="text-xs text-muted-foreground">
          {skipped} active session{skipped === 1 ? "" : "s"} hidden because consent does not include {modality}.
        </p>
      )}
    </div>
  );
}
