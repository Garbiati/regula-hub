"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Play, Loader2 } from "lucide-react";

import { DatePicker } from "@/components/ui/date-picker";
import { useIntegrationSystems } from "@/hooks/use-integration-systems";
import { useTriggerIntegration } from "@/hooks/use-trigger-integration";

function formatDateBR(d: Date): string {
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

function getDefaultDateRange(): { from: string; to: string } {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  const to = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 7);
  return { from: formatDateBR(from), to: formatDateBR(to) };
}

/** Convert dd/MM/yyyy to yyyy-MM-dd for the backend API. */
function toISO(dateBR: string): string {
  const [d, m, y] = dateBR.split("/");
  return `${y}-${m}-${d}`;
}

export interface IntegrationTriggerFormProps {
  onExecutionStarted?: (executionId: string) => void;
}

export function IntegrationTriggerForm({ onExecutionStarted }: IntegrationTriggerFormProps) {
  const t = useTranslations();
  const { data: systemsData } = useIntegrationSystems();
  const trigger = useTriggerIntegration();

  const defaults = getDefaultDateRange();
  const [systemCode, setSystemCode] = useState("");
  const [dateFrom, setDateFrom] = useState(defaults.from);
  const [dateTo, setDateTo] = useState(defaults.to);

  const systems = systemsData?.items ?? [];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const code = systemCode || systems[0]?.code;
    if (!code) return;

    trigger.mutate(
      { systemCode: code, dateFrom: toISO(dateFrom), dateTo: toISO(dateTo) },
      {
        onSuccess: (data) => {
          onExecutionStarted?.(data.id);
        },
      },
    );
  };

  return (
    <form onSubmit={handleSubmit} className="glass-card rounded-xl p-5 space-y-4">
      <h3 className="font-semibold text-[var(--text-primary)]">{t("integrations.trigger_title")}</h3>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* System selector */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-[var(--text-secondary)]">
            {t("integrations.system_label")}
          </label>
          <select
            value={systemCode || systems[0]?.code || ""}
            onChange={(e) => setSystemCode(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] px-3 py-2 text-sm text-[var(--text-primary)]"
          >
            {systems.map((s) => (
              <option key={s.code} value={s.code}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        {/* Date from */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-[var(--text-secondary)]">
            {t("integrations.date_from")}
          </label>
          <DatePicker value={dateFrom} onChange={setDateFrom} />
        </div>

        {/* Date to */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-[var(--text-secondary)]">
            {t("integrations.date_to")}
          </label>
          <DatePicker value={dateTo} onChange={setDateTo} />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={trigger.isPending || !systems.length}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-indigo)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          {trigger.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {t("integrations.trigger_button")}
        </button>
        <span className="text-xs text-[var(--text-tertiary)]">{t("integrations.default_range")}</span>
      </div>
    </form>
  );
}
