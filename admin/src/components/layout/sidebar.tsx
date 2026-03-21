"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { useRegulationSystems } from "@/hooks/use-regulation-systems";
import { buildSystemPages, SIDEBAR_ITEMS, SYSTEM_PAGES } from "@/lib/constants";
import { Circle, ICON_MAP } from "@/lib/icon-map";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/shared/logo";
import { useProfileStore } from "@/stores/profile-store";

import { Separator } from "../ui/separator";
import { NavItem } from "./nav-item";

function ActiveSystemSection() {
  const t = useTranslations();
  const pathname = usePathname();
  const system = useProfileStore((s) => s.system);
  const { data } = useRegulationSystems();

  const pages = data?.items ? buildSystemPages(data.items) : SYSTEM_PAGES;
  const config = pages[system];

  if (!config || config.children.length === 0) return null;

  const SystemIcon = ICON_MAP[config.icon] ?? Circle;

  return (
    <>
      <Separator className="my-3" />
      <div className="flex items-center gap-2 px-3 mb-2">
        <SystemIcon className="h-3.5 w-3.5 text-[var(--accent-indigo)]" />
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
          {t(config.labelKey)}
        </p>
      </div>
      {config.children.map((child) => {
        const ChildIcon = ICON_MAP[child.icon] ?? Circle;
        const isActive = pathname === child.path;
        return (
          <Link
            key={child.path}
            href={child.path}
            className={cn(
              "flex items-center gap-3 rounded-[var(--radius-nav)] px-3 py-2 text-sm font-medium transition-all ml-2",
              isActive
                ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)]"
                : "text-[var(--text-secondary)] hover:bg-[var(--accent-indigo-bg)] hover:text-[var(--accent-indigo)]",
            )}
          >
            <ChildIcon className="h-4 w-4" />
            <span>{t(child.labelKey)}</span>
          </Link>
        );
      })}
    </>
  );
}

export function Sidebar() {
  const t = useTranslations();

  return (
    <aside className="hidden w-60 flex-col glass-sidebar lg:flex border-r-0">
      <div className="flex items-center gap-2 px-4 py-4">
        <Logo size="sm" />
      </div>
      <Separator />
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">{t("nav.title")}</p>
        {SIDEBAR_ITEMS.map((item) => (
          <NavItem key={item.path} {...item} />
        ))}
        <ActiveSystemSection />
      </nav>
    </aside>
  );
}
