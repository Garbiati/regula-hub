import { Separator } from "@/components/ui/separator";

interface SectionHeaderProps {
  title: string;
}

export function SectionHeader({ title }: SectionHeaderProps) {
  return (
    <div className="flex items-center gap-3 pt-3 pb-1">
      <span className="text-xs font-semibold uppercase tracking-widest text-[var(--accent-indigo)] opacity-70">{title}</span>
      <Separator className="flex-1" />
    </div>
  );
}
