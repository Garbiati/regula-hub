"use client";

import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/lib/api-error";
import type { SearchFilters } from "@/types/appointment";

export function useExportAppointments() {
  const t = useTranslations();
  return useMutation({
    mutationFn: async (filters: SearchFilters) => {
      const blob = await apiClient.postBlob("/api/admin/sisreg/export", {
        sol_code: filters.solCode || null,
        patient_cns: filters.patientCns || null,
        patient_name: filters.patientName || null,
        cnes_solicitation: filters.cnesSolicitation || null,
        cnes_execute: filters.cnesExecute || null,
        procedure_unified_code: filters.procedureUnifiedCode || null,
        procedure_internal_code: filters.procedureInternalCode || null,
        procedure_description: filters.procedureDescription || null,
        search_type: filters.searchType,
        date_from: filters.dateFrom,
        date_to: filters.dateTo,
        situation: filters.situation,
        items_per_page: filters.itemsPerPage,
        profile_type: filters.profileType,
        usernames: filters.usernames,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sisreg_export_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    onSuccess: () => {
      toast.success(t("consulta.export_success"));
    },
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("consulta.export_error"));
    },
  });
}
