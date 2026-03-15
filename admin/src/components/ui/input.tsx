import * as React from "react";
import { Input as InputPrimitive } from "@base-ui/react/input";

import { cn } from "@/lib/utils";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        "h-8 w-full min-w-0 rounded-[var(--radius-input)] border-none bg-[rgba(120,120,128,0.08)] px-2.5 py-1 text-base font-medium text-[var(--text-primary)] transition-all outline-none file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus-visible:ring-2 focus-visible:ring-[var(--accent-indigo-ring)] disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:ring-2 aria-invalid:ring-[var(--status-danger)]/30 md:text-sm",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
