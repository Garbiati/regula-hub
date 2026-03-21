"use client";

import { useTranslations } from "next-intl";

export default function DashboardPage() {
  const t = useTranslations();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">{t("nav.dashboard")}</h1>
      <p className="text-[var(--text-secondary)]">{t("dash.no_executions")}</p>
    </div>
  );
}
