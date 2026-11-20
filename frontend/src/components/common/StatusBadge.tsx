import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { STATUS_LABELS } from "@/lib/format";
import type { SessionStatus } from "@/lib/types";

const VARIANTS: Record<SessionStatus, BadgeVariant> = {
  draft: "neutral",
  consented: "default",
  in_progress: "warning",
  completed: "success",
  failed: "destructive",
  cancelled: "neutral",
};

export function StatusBadge({ status }: { status: SessionStatus }) {
  return <Badge variant={VARIANTS[status]}>{STATUS_LABELS[status]}</Badge>;
}
