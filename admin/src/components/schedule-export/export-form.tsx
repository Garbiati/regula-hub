"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Eraser, FileSpreadsheet, FileText, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { DatePicker } from "@/components/ui/date-picker";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { FormRow } from "@/components/shared/form-row";
import { SectionHeader } from "@/components/shared/section-header";
import type { ScheduleExportFilters } from "@/types/schedule-export";

export interface ExportFormProps {
  usernames: string[];
  profileType: string;
  onSearch: (filters: ScheduleExportFilters) => void;
  onExportCsv: (filters: ScheduleExportFilters) => void;
  onExportTxt: (filters: ScheduleExportFilters) => void;
  isSearching: boolean;
  isExporting: boolean;
}

function todayStr(): string {
  const d = new Date();
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

function nextMonthStr(): string {
  const d = new Date();
  d.setMonth(d.getMonth() + 1);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}


export function ExportForm({
  usernames,
  profileType,
  onSearch,
  onExportCsv,
  onExportTxt,
  isSearching,
  isExporting,
}: ExportFormProps) {
  const t = useTranslations();
  const [dateFrom, setDateFrom] = useState(todayStr());
  const [dateTo, setDateTo] = useState(nextMonthStr());
  const [procedureFilter, setProcedureFilter] = useState("TELECONSULTA");
  const [enrich, setEnrich] = useState(true);
  const [persist, setPersist] = useState(false);

  const hasOperator = usernames.length > 0;
  const needsProcedureFilter = enrich && !procedureFilter.trim();

  const buildFilters = (): ScheduleExportFilters => ({
    dateFrom,
    dateTo,
    profileType,
    usernames,
    procedureFilter: procedureFilter || undefined,
    enrich,
    persist,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasOperator || needsProcedureFilter) return;
    onSearch(buildFilters());
  };

  const handleClear = () => {
    setDateFrom(todayStr());
    setDateTo(nextMonthStr());
    setProcedureFilter("");
    setEnrich(false);
    setPersist(false);
  };

  return (
    <Card className="glass-specular">
      <CardHeader>
        <CardTitle>{t("agendamentos.form_title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSearch} className="space-y-3.5">
          {/* ── Date range ── */}
          <SectionHeader title={t("agendamentos.section_period")} />

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
            </div>
          </FormRow>

          {/* ── Filters ── */}
          <SectionHeader title={t("agendamentos.section_filters")} />

          <FormRow label={t("agendamentos.procedure_filter")} htmlFor="procedure-filter">
            <div className="flex flex-col gap-1">
              <Input
                id="procedure-filter"
                value={procedureFilter}
                onChange={(e) => setProcedureFilter(e.target.value)}
                placeholder={t("agendamentos.procedure_placeholder")}
                className={`w-full sm:max-w-md ${needsProcedureFilter ? "border-[var(--status-danger)]" : ""}`}
              />
              {needsProcedureFilter && (
                <span className="text-[11px] text-[var(--status-danger)]">
                  {t("agendamentos.procedure_required_for_enrich")}
                </span>
              )}
            </div>
          </FormRow>

          {/* ── Enrichment ── */}
          <SectionHeader title={t("agendamentos.section_enrichment")} />

          <FormRow label={t("agendamentos.enrich_label")}>
            <div className="flex items-center gap-2">
              <Checkbox
                id="enrich-cadsus"
                checked={enrich}
                onCheckedChange={(checked) => setEnrich(checked === true)}
              />
              <Label htmlFor="enrich-cadsus" className="text-xs cursor-pointer text-[var(--text-secondary)]">
                {t("agendamentos.enrich_description")}
              </Label>
            </div>
          </FormRow>

          {/* ── Cache ── */}
          <SectionHeader title={t("agendamentos.section_cache")} />

          <FormRow label={t("agendamentos.persist_label")}>
            <div className="flex items-center gap-2">
              <Checkbox
                id="persist-db"
                checked={persist}
                onCheckedChange={(checked) => setPersist(checked === true)}
              />
              <Label htmlFor="persist-db" className="text-xs cursor-pointer text-[var(--text-secondary)]">
                {t("agendamentos.persist_description")}
              </Label>
            </div>
          </FormRow>

          {/* Operator warning */}
          {!hasOperator && (
            <p className="text-xs text-[var(--status-warning)]">
              {t("agendamentos.no_operators")}
            </p>
          )}

          {/* Action buttons */}
          <Separator className="mt-1" />
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:gap-3 pt-3">
            <Button type="submit" disabled={isSearching || !hasOperator || needsProcedureFilter} className="w-full sm:w-auto">
              {isSearching ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" data-icon="inline-start" />
              )}
              {t("agendamentos.btn_search")}
            </Button>
            <Button type="button" variant="outline" onClick={handleClear} className="w-full sm:w-auto">
              <Eraser className="mr-2 h-4 w-4" data-icon="inline-start" />
              {t("agendamentos.btn_clear")}
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={isExporting || !hasOperator}
              onClick={() => onExportCsv(buildFilters())}
              className="w-full sm:w-auto"
            >
              {isExporting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <FileSpreadsheet className="mr-2 h-4 w-4" data-icon="inline-start" />
              )}
              {t("agendamentos.btn_export_csv")}
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={isExporting || !hasOperator}
              onClick={() => onExportTxt(buildFilters())}
              className="w-full sm:w-auto"
            >
              {isExporting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <FileText className="mr-2 h-4 w-4" data-icon="inline-start" />
              )}
              {t("agendamentos.btn_export_txt")}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
