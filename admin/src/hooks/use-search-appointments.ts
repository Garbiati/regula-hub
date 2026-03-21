"use client";

import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/lib/api-error";
import type { SearchFilters, SearchResponse } from "@/types/appointment";

export function useSearchAppointments() {
  const t = useTranslations();
  return useMutation({
    mutationFn: (filters: SearchFilters) =>
      apiClient.post<SearchResponse>("/api/admin/sisreg/search", {
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
      }),
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("consulta.search_error"));
    },
  });
}
