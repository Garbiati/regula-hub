"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface RadioGroupContextValue {
  value?: string;
  onValueChange?: (value: string) => void;
}

const RadioGroupContext = React.createContext<RadioGroupContextValue>({});

interface RadioGroupProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "onChange"> {
  value?: string;
  onValueChange?: (value: string) => void;
}

function RadioGroup({ className, value, onValueChange, children, ...props }: RadioGroupProps) {
  const ctx = React.useMemo(() => ({ value, onValueChange }), [value, onValueChange]);
  return (
    <RadioGroupContext value={ctx}>
      <div data-slot="radio-group" role="radiogroup" className={cn("flex gap-3", className)} {...props}>
        {children}
      </div>
    </RadioGroupContext>
  );
}

interface RadioGroupItemProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onChange"> {
  value: string;
}

function RadioGroupItem({ className, value, id, ...props }: RadioGroupItemProps) {
  const { value: groupValue, onValueChange } = React.use(RadioGroupContext);
  const checked = value === groupValue;

  return (
    <button
      type="button"
      role="radio"
      aria-checked={checked}
      id={id}
      data-slot="radio-group-item"
      data-state={checked ? "checked" : "unchecked"}
      className={cn(
        "size-4 shrink-0 rounded-full border border-[var(--glass-border)] bg-[rgba(120,120,128,0.08)] transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-indigo-ring)]",
        "data-[state=checked]:border-[var(--accent-indigo)] data-[state=checked]:bg-[var(--accent-indigo)]",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      onClick={() => onValueChange?.(value)}
      {...props}
    >
      {checked && (
        <span className="flex items-center justify-center">
          <span className="size-1.5 rounded-full bg-white" />
        </span>
      )}
    </button>
  );
}

export { RadioGroup, RadioGroupItem };
