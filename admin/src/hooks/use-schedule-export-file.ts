"use client";

import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/lib/api-error";
import type { ScheduleExportFilters } from "@/types/schedule-export";

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

export function useScheduleExportFile() {
  const t = useTranslations();
  return useMutation({
    mutationFn: async ({ filters, format }: { filters: ScheduleExportFilters; format: "csv" | "txt" }) => {
      const blob = await apiClient.postBlob(
        `/api/admin/sisreg/schedule-export/${format}`,
        buildRequestBody(filters),
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `schedule_export_${new Date().toISOString().slice(0, 10)}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    onSuccess: () => {
      toast.success(t("agendamentos.export_success"));
    },
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("agendamentos.search_error"));
    },
  });
}
