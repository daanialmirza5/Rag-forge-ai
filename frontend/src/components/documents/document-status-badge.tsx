import { Badge } from "@/components/ui/badge";
import type { DocumentStatus } from "@/types/api";

const VARIANTS: Record<DocumentStatus, { label: string; variant: "secondary" | "warning" | "success" | "destructive" }> = {
  pending: { label: "Queued", variant: "secondary" },
  processing: { label: "Processing", variant: "warning" },
  completed: { label: "Ready", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
};

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  const { label, variant } = VARIANTS[status];
  return <Badge variant={variant}>{label}</Badge>;
}
