"use client";

import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/lib/api-error";
import type { ScheduleExportFilters, ScheduleExportResponse } from "@/types/schedule-export";

function buildRequestBody(filters: ScheduleExportFilters): Record<string, unknown> {
  return {
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
    profile_type: filters.profileType,
    usernames: filters.usernames,
    procedure_filter: filters.procedureFilter || null,
    enrich: filters.enrich ?? false,
  };
}

export function useScheduleExport() {
  const t = useTranslations();
  return useMutation({
    mutationFn: async (filters: ScheduleExportFilters) => {
      return apiClient.post<ScheduleExportResponse>(
        "/api/admin/sisreg/schedule-export",
        buildRequestBody(filters),
      );
    },
    onSuccess: (data) => {
      toast.success(`${t("agendamentos.export_success")} — ${data.total} ${t("consulta.results_count")}`);
    },
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("agendamentos.search_error"));
    },
  });
}
