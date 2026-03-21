"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { Circle, ICON_MAP } from "@/lib/icon-map";
import { cn } from "@/lib/utils";

interface NavItemProps {
  labelKey: string;
  path: string;
  icon: string;
}

export function NavItem({ labelKey, path, icon }: NavItemProps) {
  const pathname = usePathname();
  const t = useTranslations();
  const isActive = path === "/" ? pathname === "/" : pathname.startsWith(path);

  const IconComponent = ICON_MAP[icon] ?? Circle;

  return (
    <Link
      href={path}
      className={cn(
        "flex items-center gap-3 rounded-[var(--radius-nav)] px-3 py-2 text-sm font-medium transition-all duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]",
        isActive
          ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] shadow-[inset_0_1px_0_rgba(255,255,255,0.5)]"
          : "text-[var(--text-secondary)] hover:bg-[var(--accent-indigo-bg)] hover:text-[var(--accent-indigo)]",
      )}
    >
      <IconComponent className="h-4 w-4" />
      <span>{t(labelKey)}</span>
    </Link>
  );
}
