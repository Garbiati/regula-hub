"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Play, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import { FormRow } from "@/components/shared/form-row";
import { SectionHeader } from "@/components/shared/section-header";
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
    <Card className="glass-specular">
      <CardHeader>
        <CardTitle>{t("integrations.trigger_title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3.5">
          <SectionHeader title={t("integrations.section_target")} />

          <FormRow label={t("integrations.system_label")}>
            <select
              value={systemCode || systems[0]?.code || ""}
              onChange={(e) => setSystemCode(e.target.value)}
              className="w-full sm:max-w-xs rounded-[var(--radius-input)] border border-[var(--glass-border)] bg-[var(--glass-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-indigo)]/30"
            >
              {systems.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.name}
                </option>
              ))}
            </select>
          </FormRow>

          <SectionHeader title={t("integrations.section_period")} />

          <FormRow label={t("consulta.period")}>
            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-[var(--text-tertiary)]">{t("common.from")}</span>
                <DatePicker value={dateFrom} onChange={setDateFrom} />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-[var(--text-tertiary)]">{t("common.to")}</span>
                <DatePicker value={dateTo} onChange={setDateTo} />
              </div>
              <span className="text-[11px] text-[var(--text-tertiary)] italic">{t("integrations.default_range")}</span>
            </div>
          </FormRow>

          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:gap-3 pt-4">
            <Button type="submit" disabled={trigger.isPending || !systems.length} className="w-full sm:w-auto">
              {trigger.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" data-icon="inline-start" />
              )}
              {t("integrations.trigger_button")}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
