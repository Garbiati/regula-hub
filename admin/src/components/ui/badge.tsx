import { mergeProps } from "@base-ui/react/merge-props";
import { useRender } from "@base-ui/react/use-render";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "group/badge inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-all focus-visible:ring-2 focus-visible:ring-[var(--accent-indigo-ring)] has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&>svg]:pointer-events-none [&>svg]:size-3!",
  {
    variants: {
      variant: {
        default: "border-[var(--accent-indigo)]/20 bg-[var(--accent-indigo-bg)] text-[var(--accent-indigo)] [backdrop-filter:var(--glass-blur)] [-webkit-backdrop-filter:var(--glass-blur)]",
        secondary: "border-[var(--glass-border-subtle)] bg-[var(--glass-surface)] text-[var(--text-secondary)] [backdrop-filter:var(--glass-blur)] [-webkit-backdrop-filter:var(--glass-blur)]",
        destructive:
          "border-[var(--status-danger)]/20 bg-[var(--status-danger)]/8 text-[var(--status-danger)]",
        outline: "border-[var(--glass-border-subtle)] text-[var(--text-primary)] bg-transparent",
        ghost: "border-transparent hover:bg-[var(--accent-indigo-bg)] hover:text-[var(--accent-indigo)]",
        link: "border-transparent text-[var(--accent-indigo)] underline-offset-4 hover:underline",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

function Badge({
  className,
  variant = "default",
  render,
  ...props
}: useRender.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return useRender({
    defaultTagName: "span",
    props: mergeProps<"span">(
      {
        className: cn(badgeVariants({ variant }), className),
      },
      props,
    ),
    render,
    state: {
      slot: "badge",
      variant,
    },
  });
}

export { Badge, badgeVariants };
