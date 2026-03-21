import { Loader2, ShieldCheck, ShieldX, XCircle } from "lucide-react";

export type ValidationStatus = "idle" | "checking" | "valid" | "invalid" | "error";

interface StatusBadgeProps {
  status: ValidationStatus;
  labels: {
    notVerified: string;
    verifying: string;
    valid: string;
    invalid: string;
    error: string;
  };
}

export function StatusBadge({ status, labels }: StatusBadgeProps) {
  switch (status) {
    case "idle":
      return (
        <span className="flex items-center gap-1 text-xs text-[var(--text-tertiary)]">
          {labels.notVerified}
        </span>
      );
    case "checking":
      return (
        <span className="flex items-center gap-1 text-xs text-[var(--text-secondary)]">
          <Loader2 className="h-3 w-3 animate-spin" />
          {labels.verifying}
        </span>
      );
    case "valid":
      return (
        <span className="flex items-center gap-1 text-xs text-[var(--status-success)]">
          <ShieldCheck className="h-3.5 w-3.5" />
          {labels.valid}
        </span>
      );
    case "invalid":
      return (
        <span className="flex items-center gap-1 text-xs text-[var(--status-danger)]">
          <ShieldX className="h-3.5 w-3.5" />
          {labels.invalid}
        </span>
      );
    case "error":
      return (
        <span className="flex items-center gap-1 text-xs text-[var(--status-warning)]">
          <XCircle className="h-3.5 w-3.5" />
          {labels.error}
        </span>
      );
  }
}
