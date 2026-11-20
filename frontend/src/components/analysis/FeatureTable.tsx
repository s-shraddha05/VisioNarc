import { Cpu, Monitor, Server } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { FeatureCatalogue, FeatureSpec, Measurement, Modality, Provenance } from "@/lib/types";

let cataloguePromise: Promise<FeatureCatalogue> | null = null;

/** The feature catalogue rarely changes; fetch once per page load. */
export function useFeatureCatalogue(): FeatureCatalogue | null {
  const [data, setData] = useState<FeatureCatalogue | null>(null);
  useEffect(() => {
    cataloguePromise ??= api.featureSchema().catch((err) => {
      cataloguePromise = null;
      throw err;
    });
    cataloguePromise.then(setData).catch(() => setData(null));
  }, []);
  return data;
}

const PROVENANCE_UI: Record<Provenance, { label: string; icon: typeof Server; variant: "default" | "neutral" | "warning" }> = {
  server_audio: { label: "Server · audio", icon: Server, variant: "default" },
  server_landmarks: { label: "Server · landmarks", icon: Server, variant: "default" },
  browser_pixels: { label: "Browser · pixels", icon: Monitor, variant: "warning" },
  browser_model: { label: "Browser · model", icon: Cpu, variant: "neutral" },
};

export function ProvenanceBadge({ provenance, title }: { provenance: Provenance; title?: string }) {
  const ui = PROVENANCE_UI[provenance];
  return (
    <Badge variant={ui.variant} title={title}>
      <ui.icon /> {ui.label}
    </Badge>
  );
}

export function formatFeatureValue(value: unknown, unit = ""): string {
  if (value === null || value === undefined) return "not measured";
  if (Array.isArray(value)) return `${value.length} values`;
  if (typeof value === "object") return `${Object.keys(value as object).length} coefficients`;
  if (typeof value === "number") {
    const abs = Math.abs(value);
    const text = abs !== 0 && (abs < 0.001 || abs >= 100000) ? value.toExponential(2) : String(Number(value.toPrecision(4)));
    const suffix = unit && !["count", "ratio", "fraction", "0–1", "CV", "per sample"].includes(unit) ? ` ${unit}` : "";
    return text + suffix;
  }
  return String(value);
}

/** All stored features of one measurement, labelled with unit and where each value was computed. */
export function FeatureTable({ modality, measurement }: { modality: Modality; measurement: Measurement }) {
  const catalogue = useFeatureCatalogue();
  const specs: FeatureSpec[] = catalogue?.features.filter((f) => f.modality === modality) ?? [];
  const rows = specs.length
    ? specs.map((s) => ({ spec: s, value: measurement.features[s.key] }))
    : Object.entries(measurement.features).map(([key, value]) => ({ spec: null, key, value }));

  return (
    <div className="relative overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="py-2 pr-4 font-medium">Measurement</th>
            <th className="py-2 pr-4 font-medium">Value</th>
            <th className="py-2 font-medium">Computed</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map((row) => {
            const key = row.spec?.key ?? (row as { key: string }).key;
            const nested = row.value && typeof row.value === "object" && !Array.isArray(row.value);
            return (
              <tr key={key} className="align-top">
                <td className="py-2 pr-4">
                  <span className="font-medium">{row.spec?.label ?? key}</span>
                  {row.spec && <span className="block text-xs text-muted-foreground">{row.spec.description}</span>}
                </td>
                <td className="py-2 pr-4 tabular-nums">
                  {nested ? (
                    <ul className="space-y-0.5 text-xs">
                      {Object.entries(row.value as Record<string, unknown>).map(([k, v]) => (
                        <li key={k}>
                          {k}: {formatFeatureValue(v)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className={row.value === null ? "text-muted-foreground" : undefined}>
                      {formatFeatureValue(row.value, row.spec?.unit)}
                    </span>
                  )}
                </td>
                <td className="py-2">
                  {row.spec && <ProvenanceBadge provenance={row.spec.provenance} title={catalogue?.provenance[row.spec.provenance]} />}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
