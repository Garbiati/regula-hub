import { Label } from "@/components/ui/label";

interface FormRowProps {
  label: string;
  htmlFor?: string;
  children: React.ReactNode;
}

export function FormRow({ label, htmlFor, children }: FormRowProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
      <Label htmlFor={htmlFor} className="text-xs font-medium text-[var(--text-secondary)] sm:w-32 md:w-40 sm:text-right shrink-0">
        {label}
      </Label>
      <div className="flex-1">{children}</div>
    </div>
  );
}
