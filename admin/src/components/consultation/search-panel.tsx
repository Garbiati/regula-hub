"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Download, Eraser, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { FormRow } from "@/components/shared/form-row";
import { SectionHeader } from "@/components/shared/section-header";
import { useFormMetadata } from "@/hooks/use-form-metadata";
import { filterSituationsBySearchType, resolveLabel } from "@/lib/form-metadata-utils";
import { useProfileStore } from "@/stores/profile-store";
import type { SearchFilters } from "@/types/appointment";
import type { FormOptionItem } from "@/types/form-metadata";

export interface SearchPanelProps {
  onSearch: (filters: SearchFilters) => void;
  onExport: (filters: SearchFilters) => void;
  onCodeSearch: (code: string) => void;
  isPending: boolean;
  isExporting: boolean;
}

function todayStr(): string {
  const d = new Date();
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
}

// Static fallbacks — used when the form metadata API is unavailable
const FALLBACK_SITUATION_OPTIONS: Record<string, { value: string; labelKey: string }[]> = {
  solicitacao: [
    { value: "1", labelKey: "consulta.sit_sol_pending_regulation" },
    { value: "2", labelKey: "consulta.sit_sol_pending_queue" },
    { value: "3", labelKey: "consulta.sit_sol_cancelled" },
    { value: "4", labelKey: "consulta.sit_sol_returned" },
    { value: "5", labelKey: "consulta.sit_sol_resent" },
    { value: "6", labelKey: "consulta.sit_sol_denied" },
    { value: "7", labelKey: "consulta.sit_sol_scheduled" },
    { value: "9", labelKey: "consulta.sit_sol_scheduled_queue" },
    { value: "10", labelKey: "consulta.sit_sched_cancelled" },
    { value: "11", labelKey: "consulta.sit_sched_confirmed" },
    { value: "12", labelKey: "consulta.sit_sched_absent" },
  ],
  agendamento: [
    { value: "7", labelKey: "consulta.sit_sol_scheduled" },
    { value: "9", labelKey: "consulta.sit_sol_scheduled_queue" },
    { value: "10", labelKey: "consulta.sit_sched_cancelled" },
    { value: "11", labelKey: "consulta.sit_sched_confirmed" },
    { value: "12", labelKey: "consulta.sit_sched_absent" },
  ],
  execucao: [
    { value: "7", labelKey: "consulta.sit_sol_scheduled" },
    { value: "9", labelKey: "consulta.sit_sol_scheduled_queue" },
    { value: "10", labelKey: "consulta.sit_sched_cancelled" },
    { value: "11", labelKey: "consulta.sit_sched_confirmed" },
    { value: "12", labelKey: "consulta.sit_sched_absent" },
  ],
  confirmacao: [
    { value: "11", labelKey: "consulta.sit_sched_confirmed" },
  ],
  cancelamento: [
    { value: "3", labelKey: "consulta.sit_sol_cancelled" },
    { value: "10", labelKey: "consulta.sit_sched_cancelled" },
  ],
};

const FALLBACK_SEARCH_TYPES = ["solicitacao", "agendamento", "execucao", "confirmacao", "cancelamento"];

const FALLBACK_ITEMS_PER_PAGE_OPTIONS = [
  { value: "10", labelKey: "10" },
  { value: "20", labelKey: "20" },
  { value: "50", labelKey: "50" },
  { value: "100", labelKey: "100" },
  { value: "0", labelKey: "consulta.items_all" },
];


export function SearchPanel({ onSearch, onExport, onCodeSearch, isPending, isExporting }: SearchPanelProps) {
  const t = useTranslations();
  const { profile, selectedUsers } = useProfileStore();
  const { data: formMetadata } = useFormMetadata("SISREG", "search_appointments");

  // Derive dynamic options with static fallbacks
  const searchTypes: FormOptionItem[] = formMetadata?.searchTypes
    ?? FALLBACK_SEARCH_TYPES.map((v) => ({ value: v, labelKey: `consulta.type_${v}` }));

  // Identification
  const [solCode, setSolCode] = useState("");
  const [patientCns, setPatientCns] = useState("");
  const [patientName, setPatientName] = useState("");
  const [cnesSolicitation, setCnesSolicitation] = useState("");
  const [cnesExecute, setCnesExecute] = useState("");

  // Procedure
  const [procedureUnifiedCode, setProcedureUnifiedCode] = useState("");
  const [procedureInternalCode, setProcedureInternalCode] = useState("");
  const [procedureDescription, setProcedureDescription] = useState("");

  // Date/Period
  const [searchType, setSearchType] = useState("agendamento");
  const [dateFrom, setDateFrom] = useState(todayStr());
  const [dateTo, setDateTo] = useState(todayStr());

  // Status
  const [situation, setSituation] = useState("7");
  const [itemsPerPage, setItemsPerPage] = useState("20");

  const hasOperator = selectedUsers.length > 0;

  const buildFilters = (): SearchFilters => ({
    solCode: solCode || undefined,
    patientCns: patientCns || undefined,
    patientName: patientName || undefined,
    cnesSolicitation: cnesSolicitation || undefined,
    cnesExecute: cnesExecute || undefined,
    procedureUnifiedCode: procedureUnifiedCode || undefined,
    procedureInternalCode: procedureInternalCode || undefined,
    procedureDescription: procedureDescription || undefined,
    searchType,
    dateFrom,
    dateTo,
    situation,
    itemsPerPage,
    profileType: profile.toUpperCase(),
    usernames: selectedUsers,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasOperator) return;

    // If only solicitation code is filled, do a direct code lookup
    if (solCode.trim() && !patientCns && !patientName && !cnesSolicitation && !cnesExecute) {
      onCodeSearch(solCode.trim());
      return;
    }

    onSearch(buildFilters());
  };

  const handleExport = () => {
    if (!hasOperator) return;
    onExport(buildFilters());
  };

  const handleClear = () => {
    setSolCode("");
    setPatientCns("");
    setPatientName("");
    setCnesSolicitation("");
    setCnesExecute("");
    setProcedureUnifiedCode("");
    setProcedureInternalCode("");
    setProcedureDescription("");
    setSearchType("agendamento");
    setDateFrom(todayStr());
    setDateTo(todayStr());
    setSituation("7");
    setItemsPerPage("20");
  };

  const getSituationsForType = (type: string): FormOptionItem[] => {
    if (formMetadata) {
      return filterSituationsBySearchType(formMetadata.situations, type);
    }
    return (FALLBACK_SITUATION_OPTIONS[type] ?? FALLBACK_SITUATION_OPTIONS["agendamento"]!).map(
      (o) => ({ value: o.value, labelKey: o.labelKey }),
    );
  };

  const handleSearchTypeChange = (value: string) => {
    setSearchType(value);
    const options = getSituationsForType(value);
    if (options[0]) {
      setSituation(options[0].value);
    }
  };

  const situationOptions = getSituationsForType(searchType);

  const itemsPerPageOptions: FormOptionItem[] = formMetadata?.itemsPerPage
    ?? FALLBACK_ITEMS_PER_PAGE_OPTIONS.map((o) => ({ value: o.value, labelKey: o.labelKey }));

  return (
    <Card className="glass-specular">
      <CardHeader>
        <CardTitle>{t("consulta.form_title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSearch} className="space-y-3.5">
          {/* ── Identification ── */}
          <FormRow label={t("consulta.field_sol_code")} htmlFor="sol-code">
            <Input
              id="sol-code"
              value={solCode}
              onChange={(e) => setSolCode(e.target.value)}
              placeholder={t("consulta.code_placeholder")}
              className="w-full sm:max-w-xs font-mono"
            />
          </FormRow>

          <FormRow label={t("consulta.field_patient_cns_search")} htmlFor="patient-cns">
            <Input
              id="patient-cns"
              value={patientCns}
              onChange={(e) => setPatientCns(e.target.value)}
              placeholder="CNS"
              className="w-full sm:max-w-xs font-mono"
            />
          </FormRow>

          <FormRow label={t("consulta.field_patient_name_search")} htmlFor="patient-name">
            <Input
              id="patient-name"
              value={patientName}
              onChange={(e) => setPatientName(e.target.value)}
              className="w-full sm:max-w-md"
            />
          </FormRow>

          <FormRow label={t("consulta.field_cnes_solicitation")} htmlFor="cnes-solicitation">
            <Input
              id="cnes-solicitation"
              value={cnesSolicitation}
              onChange={(e) => setCnesSolicitation(e.target.value)}
              placeholder="CNES"
              className="w-full sm:max-w-xs font-mono"
            />
          </FormRow>

          <FormRow label={t("consulta.field_cnes_execute")} htmlFor="cnes-execute">
            <Input
              id="cnes-execute"
              value={cnesExecute}
              onChange={(e) => setCnesExecute(e.target.value)}
              placeholder="CNES"
              className="w-full sm:max-w-xs font-mono"
            />
          </FormRow>

          {/* ── Procedure ── */}
          <SectionHeader title={t("consulta.section_procedure_search")} />

          <FormRow label={t("consulta.field_unified_code")} htmlFor="procedure-unified-code">
            <Input
              id="procedure-unified-code"
              value={procedureUnifiedCode}
              onChange={(e) => setProcedureUnifiedCode(e.target.value)}
              className="w-full sm:max-w-xs font-mono"
            />
          </FormRow>

          <FormRow label={t("consulta.field_internal_code")} htmlFor="procedure-internal-code">
            <Input
              id="procedure-internal-code"
              value={procedureInternalCode}
              onChange={(e) => setProcedureInternalCode(e.target.value)}
              className="w-full sm:max-w-xs font-mono"
            />
          </FormRow>

          <FormRow label={t("consulta.field_description")} htmlFor="procedure-description">
            <Input
              id="procedure-description"
              value={procedureDescription}
              onChange={(e) => setProcedureDescription(e.target.value)}
              className="w-full sm:max-w-md"
            />
          </FormRow>

          {/* ── Date/Period ── */}
          <SectionHeader title={t("consulta.section_period")} />

          <FormRow label={t("consulta.field_search_type")}>
            <RadioGroup
              value={searchType}
              onValueChange={handleSearchTypeChange}
              className="grid grid-cols-2 gap-x-4 gap-y-2 sm:flex sm:flex-wrap sm:gap-x-4 sm:gap-y-2"
            >
              {searchTypes.map((st) => (
                <div key={st.value} className="flex items-center gap-1.5">
                  <RadioGroupItem value={st.value} id={`search-type-${st.value}`} />
                  <Label htmlFor={`search-type-${st.value}`} className="text-xs cursor-pointer">
                    {resolveLabel(t, st)}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </FormRow>

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

          {/* ── Status ── */}
          <SectionHeader title={t("consulta.section_status")} />

          <FormRow label={t("consulta.field_situation")}>
            <Select value={situation} onValueChange={(v) => v && setSituation(v)}>
              <SelectTrigger className="w-full sm:max-w-xs">
                <SelectValue>
                  {resolveLabel(t, situationOptions.find((o) => o.value === situation) ?? { value: situation })}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {situationOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {resolveLabel(t, opt)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormRow>

          <FormRow label={t("consulta.field_items_per_page")}>
            <Select value={itemsPerPage} onValueChange={(v) => v && setItemsPerPage(v)}>
              <SelectTrigger className="w-full sm:max-w-xs">
                <SelectValue>
                  {resolveLabel(t, itemsPerPageOptions.find((o) => o.value === itemsPerPage) ?? { value: itemsPerPage })}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {itemsPerPageOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {resolveLabel(t, opt)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormRow>

          {/* Operator warning */}
          {!hasOperator && (
            <p className="text-xs text-[var(--status-warning)]">
              {t("consulta.no_operator_warning")}
            </p>
          )}

          {/* Action buttons */}
          <Separator className="mt-1" />
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:gap-3 pt-3">
            <Button type="submit" disabled={isPending || !hasOperator} className="w-full sm:w-auto">
              {isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" data-icon="inline-start" />
              )}
              {t("consulta.btn_search")}
            </Button>
            <Button type="button" variant="outline" onClick={handleClear} className="w-full sm:w-auto">
              <Eraser className="mr-2 h-4 w-4" data-icon="inline-start" />
              {t("consulta.btn_clear")}
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={isExporting || !hasOperator}
              onClick={handleExport}
              className="w-full sm:w-auto"
            >
              {isExporting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" data-icon="inline-start" />
              )}
              {t("consulta.btn_export_csv")}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
