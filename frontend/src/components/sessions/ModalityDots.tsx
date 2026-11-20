import { Activity, AudioLines, ScanFace } from "lucide-react";
import type { SessionSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Consent per modality, plus how many measurements exist for it. */
export function ModalityDots({ session }: { session: SessionSummary }) {
  const items = [
    { label: "Face", icon: ScanFace, allowed: session.allow_face, count: session.counts.face },
    { label: "Motion", icon: Activity, allowed: session.allow_motion, count: session.counts.motion },
    { label: "Voice", icon: AudioLines, allowed: session.allow_voice, count: session.counts.voice },
  ];
  return (
    <div className="flex items-center gap-1.5">
      {items.map((m) => (
        <span
          key={m.label}
          title={`${m.label}: ${m.allowed ? "consented" : "not consented"}, ${m.count} measurement${m.count === 1 ? "" : "s"}`}
          className={cn(
            "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs tabular-nums",
            m.allowed ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground/50 line-through",
          )}
        >
          <m.icon className="size-3.5" aria-hidden="true" />
          <span className="sr-only">{m.label}</span>
          {m.allowed ? m.count : "–"}
        </span>
      ))}
    </div>
  );
}
