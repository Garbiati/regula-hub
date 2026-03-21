"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Toaster } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { OperatorContextBar } from "@/components/consultation/operator-context-bar";
import { PipelineModal } from "@/components/consultation/pipeline-modal";
import { ExportForm } from "@/components/schedule-export/export-form";
import { ExportResultsTable } from "@/components/schedule-export/export-results-table";
import { useExportPipeline } from "@/hooks/use-export-pipeline";
import { useScheduleExportFile } from "@/hooks/use-schedule-export-file";
import { useProfileStore } from "@/stores/profile-store";
import type { ScheduleExportFilters } from "@/types/schedule-export";

export default function SisregAgendamentosPage() {
  const t = useTranslations();
  const profile = useProfileStore((s) => s.profile);
  const selectedUsers = useProfileStore((s) => s.selectedUsers);

  const {
    pipelineState,
    results,
    isModalOpen,
    isConfirmed,
    startExport,
    retryOperator,
    retryEnrichment,
    confirmResults,
    cancel,
    reset,
    isExporting,
  } = useExportPipeline();
  const exportFile = useScheduleExportFile();
  const [enrichEnabled, setEnrichEnabled] = useState(false);
  const [cacheEnabled, setCacheEnabled] = useState(false);

  const handleSearch = (filters: ScheduleExportFilters) => {
    setEnrichEnabled(filters.enrich ?? false);
    setCacheEnabled(filters.persist ?? false);
    reset();
    startExport(filters);
  };

  const handleExportCsv = (filters: ScheduleExportFilters) => {
    exportFile.mutate({ filters, format: "csv" });
  };

  const handleExportTxt = (filters: ScheduleExportFilters) => {
    exportFile.mutate({ filters, format: "txt" });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader title={t("nav.sisreg_agendamentos")} />

      {/* Operator context bar */}
      <div className="animate-fadeInUp-2">
        <OperatorContextBar />
      </div>

      {/* Export form */}
      <div className="animate-fadeInUp-3">
        <ExportForm
          usernames={selectedUsers}
          profileType={profile.toUpperCase()}
          onSearch={handleSearch}
          onExportCsv={handleExportCsv}
          onExportTxt={handleExportTxt}
          isSearching={isExporting || isModalOpen}
          isExporting={exportFile.isPending}
        />
      </div>

      {/* Results table — only shown after user confirms in the modal */}
      {isConfirmed && results.length > 0 && (
        <div className="animate-fadeInUp-4">
          <ExportResultsTable
            items={results}
            total={results.length}
            operatorsQueried={pipelineState.operators.length}
            operatorsSucceeded={pipelineState.operators.filter((op) => op.status === "success").length}
            enriched={enrichEnabled}
          />
        </div>
      )}

      {/* Pipeline modal — full interactive pipeline visualization */}
      <PipelineModal
        open={isModalOpen}
        state={pipelineState}
        onRetryOperator={retryOperator}
        onRetryEnrichment={retryEnrichment}
        onConfirm={confirmResults}
        onCancel={cancel}
        enrichEnabled={enrichEnabled}
        cacheEnabled={cacheEnabled}
      />

      <Toaster />
    </div>
  );
}
