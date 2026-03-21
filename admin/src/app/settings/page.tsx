"use client";

import { CheckCircle, Globe, Info, Server, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useHealthCheck } from "@/hooks/use-health-check";
import { getStoredLocale, locales, type Locale } from "@/i18n/config";
import { setAppLocale } from "@/providers/i18n-provider";

const localeLabels: Record<Locale, string> = {
  "pt-BR": "Portugues (Brasil)",
  "en-US": "English (US)",
  "es-AR": "Espanol (Argentina)",
};

export default function SettingsPage() {
  const t = useTranslations();
  const { refetch, data, isError, isFetching } = useHealthCheck();

  const [currentLocale, setCurrentLocale] = useState<Locale>(getStoredLocale);

  function handleLocaleChange(newLocale: Locale) {
    setCurrentLocale(newLocale);
    setAppLocale(newLocale);
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">{t("settings.title")}</h1>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Language */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-[var(--accent-indigo)]" />
              {t("settings.language")}
            </CardTitle>
            <CardDescription>{t("settings.language_desc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <select
              value={currentLocale}
              onChange={(e) => handleLocaleChange(e.target.value as Locale)}
              className="w-full rounded-[var(--radius-input)] border-none bg-[rgba(120,120,128,0.08)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] outline-none focus:ring-2 focus:ring-[var(--accent-indigo-ring)]"
            >
              {locales.map((loc) => (
                <option key={loc} value={loc}>
                  {localeLabels[loc]}
                </option>
              ))}
            </select>
          </CardContent>
        </Card>

        {/* API Connection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5 text-[var(--accent-indigo)]" />
              {t("settings.api_connection")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <span className="text-sm font-medium text-[var(--text-secondary)]">{t("settings.api_url")}</span>
              <p className="mt-1 rounded-[var(--radius-input)] bg-[rgba(120,120,128,0.08)] px-3 py-2 font-mono text-sm text-[var(--text-primary)]">{apiUrl}</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-[var(--text-secondary)]">{t("settings.api_status")}</span>
              {data ? (
                <span className="flex items-center gap-1 text-sm text-[var(--status-success)]">
                  <CheckCircle className="h-4 w-4" />
                  {t("settings.api_connected")}
                </span>
              ) : isError ? (
                <span className="flex items-center gap-1 text-sm text-[var(--status-danger)]">
                  <XCircle className="h-4 w-4" />
                  {t("settings.api_disconnected")}
                </span>
              ) : null}
            </div>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="rounded-full bg-[var(--accent-indigo)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-indigo-light)] disabled:opacity-50 transition-all"
            >
              {isFetching ? t("api.loading") : t("settings.api_test")}
            </button>
          </CardContent>
        </Card>

        {/* About */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="h-5 w-5 text-[var(--accent-indigo)]" />
              {t("settings.about")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">{t("settings.version")}</span>
              <span className="font-medium text-[var(--text-primary)]">0.1.0</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">{t("settings.environment")}</span>
              <span className="font-medium text-[var(--text-primary)]">
                {process.env.NODE_ENV ?? "development"}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Next.js</span>
              <span className="font-medium text-[var(--text-primary)]">16</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
