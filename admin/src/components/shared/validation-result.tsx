import { CheckCircle, XCircle } from "lucide-react";

interface ValidationResultProps {
  valid: boolean;
  validLabel: string;
  invalidLabel: string;
}

export function ValidationResult({ valid, validLabel, invalidLabel }: ValidationResultProps) {
  return (
    <span className="flex items-center gap-1.5 text-sm">
      {valid ? (
        <>
          <CheckCircle className="h-4 w-4 text-[var(--status-success)]" />
          <span className="text-[var(--status-success)]">{validLabel}</span>
        </>
      ) : (
        <>
          <XCircle className="h-4 w-4 text-[var(--status-danger)]" />
          <span className="text-[var(--status-danger)]">{invalidLabel}</span>
        </>
      )}
    </span>
  );
}
