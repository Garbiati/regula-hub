"use client";

import { Button as ButtonPrimitive } from "@base-ui/react/button";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-full border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-all duration-200 ease-[cubic-bezier(0.4,0,0.2,1)] outline-none select-none focus-visible:ring-2 focus-visible:ring-[var(--accent-indigo-ring)] active:scale-[0.97] disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-destructive/20 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--accent-indigo)] text-white shadow-md hover:bg-[var(--accent-indigo-light)] hover:shadow-[0_4px_16px_rgba(88,86,214,0.25)] hover:scale-[1.02] active:scale-[0.97]",
        outline:
          "border-[var(--glass-border)] bg-[var(--glass-surface)] [backdrop-filter:var(--glass-blur)] [-webkit-backdrop-filter:var(--glass-blur)] hover:bg-[var(--glass-surface-hover)] hover:shadow-[var(--glass-shadow)] aria-expanded:bg-[var(--glass-surface-hover)]",
        secondary:
          "bg-[var(--glass-surface)] [backdrop-filter:var(--glass-blur)] [-webkit-backdrop-filter:var(--glass-blur)] border-[var(--glass-border)] text-[var(--text-primary)] hover:bg-[var(--glass-surface-hover)] hover:shadow-[var(--glass-shadow)]",
        ghost:
          "hover:bg-[var(--accent-indigo-bg)] hover:text-[var(--accent-indigo)] aria-expanded:bg-[var(--accent-indigo-bg)]",
        destructive:
          "bg-[var(--status-danger)]/10 text-[var(--status-danger)] hover:bg-[var(--status-danger)]/20 focus-visible:ring-[var(--status-danger)]/30",
        link: "text-[var(--accent-indigo)] underline-offset-4 hover:underline",
      },
      size: {
        default:
          "h-8 gap-1.5 px-4 has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3",
        xs: "h-6 gap-1 px-3 text-xs has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 gap-1 px-3 text-[0.8rem] has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-9 gap-1.5 px-5 has-data-[icon=inline-end]:pr-4 has-data-[icon=inline-start]:pl-4",
        icon: "size-8",
        "icon-xs":
          "size-6 [&_svg:not([class*='size-'])]:size-3",
        "icon-sm":
          "size-7",
        "icon-lg": "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
