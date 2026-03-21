"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Toaster } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { OperatorContextBar } from "@/components/consultation/operator-context-bar";
import { SearchPanel } from "@/components/consultation/search-panel";
import { ResultsTable } from "@/components/consultation/results-table";
import { DetailDialog } from "@/components/consultation/detail-dialog";
import { PipelineModal } from "@/components/consultation/pipeline-modal";
import { useExportAppointments } from "@/hooks/use-export-appointments";
import { usePipelineSearch } from "@/hooks/use-pipeline-search";
import { useProfileStore } from "@/stores/profile-store";
import type { SearchFilters } from "@/types/appointment";

export default function SisregConsultaPage() {
  const t = useTranslations();
  const profile = useProfileStore((s) => s.profile);
  const selectedUsers = useProfileStore((s) => s.selectedUsers);
  const exportMutation = useExportAppointments();
  const {
    pipelineState,
    results,
    isModalOpen,
    isConfirmed,
    startSearch,
    retryOperator,
    confirmResults,
    cancel,
    reset,
    isSearching,
  } = usePipelineSearch();

  const [selectedCode, setSelectedCode] = useState<string | null>(null);

  const primaryUser = selectedUsers[0] ?? "";

  const handleSearch = (filters: SearchFilters) => {
    setSelectedCode(null);
    reset();
    startSearch(filters);
  };

  const handleExport = (filters: SearchFilters) => {
    exportMutation.mutate(filters);
  };

  const handleCodeSearch = (code: string) => {
    setSelectedCode(code);
  };

  return (
    <div className="space-y-6">
      {/* Header row */}
      <PageHeader title={t("nav.sisreg_consulta")} />

      {/* Operator context bar — inline profile + operator switcher */}
      <div className="animate-fadeInUp-2">
        <OperatorContextBar />
      </div>

      {/* Search form */}
      <div className="animate-fadeInUp-3">
        <SearchPanel
          onSearch={handleSearch}
          onExport={handleExport}
          onCodeSearch={handleCodeSearch}
          isPending={isSearching || isModalOpen}
          isExporting={exportMutation.isPending}
        />
      </div>

      {/* Results table — only shown after user confirms in the modal */}
      {isConfirmed && results.length > 0 && (
        <div className="animate-fadeInUp-4">
          <ResultsTable
            items={results}
            total={results.length}
            onRowClick={setSelectedCode}
          />
        </div>
      )}

      {/* Pipeline modal — full interactive pipeline visualization */}
      <PipelineModal
        open={isModalOpen}
        state={pipelineState}
        onRetryOperator={retryOperator}
        onConfirm={confirmResults}
        onCancel={cancel}
      />

      {/* Detail dialog */}
      <DetailDialog
        code={selectedCode}
        username={primaryUser}
        profileType={profile.toUpperCase()}
        open={!!selectedCode}
        onClose={() => setSelectedCode(null)}
      />

      <Toaster />
    </div>
  );
}
