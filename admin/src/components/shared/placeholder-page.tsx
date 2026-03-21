"use client";

import { useTranslations } from "next-intl";

import { Construction, ICON_MAP } from "@/lib/icon-map";

interface PlaceholderPageProps {
  systemName: string;
  icon: string;
}

export function PlaceholderPage({ systemName, icon }: PlaceholderPageProps) {
  const t = useTranslations();
  const IconComponent = ICON_MAP[icon] ?? Construction;

  return (
    <div className="flex flex-col items-center justify-center py-24">
      <IconComponent className="mb-4 h-16 w-16 text-[var(--text-tertiary)]" />
      <h2 className="mb-2 text-xl font-semibold text-[var(--text-primary)]">{systemName}</h2>
      <p className="text-[var(--text-secondary)]">{t("placeholder.message")}</p>
    </div>
  );
}
