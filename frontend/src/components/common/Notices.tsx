import { FlaskConical, Lock, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Persistent reminder of what the system can and cannot conclude. */
export function ResearchNotice({ className, children }: { className?: string; children?: ReactNode }) {
  return (
    <div className={cn("flex gap-3 rounded-lg border border-primary/25 bg-primary/5 px-4 py-3 text-sm", className)}>
      <FlaskConical className="mt-0.5 size-4 shrink-0 text-primary" />
      <p className="text-foreground/85">
        {children ?? (
          <>
            <strong className="font-semibold">Experimental research prototype.</strong> Facial appearance, voice
            and movement cannot prove drug consumption. Outputs are behavioural indicators with stated
            uncertainty, never a medical or forensic diagnosis.
          </>
        )}
      </p>
    </div>
  );
}

/** Explains why a control is disabled: the backend does not provide the feature yet. */
export function UnavailableNotice({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn("flex gap-3 rounded-lg border border-dashed bg-muted/50 px-4 py-3 text-sm", className)}>
      <Lock className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
      <div className="space-y-0.5">
        <p className="font-medium">{title}</p>
        <p className="text-muted-foreground">{children}</p>
      </div>
    </div>
  );
}

export function PrivacyNotice({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("flex gap-3 rounded-lg border bg-card px-4 py-3 text-sm", className)}>
      <ShieldCheck className="mt-0.5 size-4 shrink-0 text-success" />
      <p className="text-muted-foreground">{children}</p>
    </div>
  );
}
