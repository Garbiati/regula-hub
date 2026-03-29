import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/lib/api-error";
import { queryKeys } from "@/lib/query-keys";
import type {
  AppointmentListResponse,
  AppointmentStatusCounts,
  AppointmentUpdateRequest,
  IntegrationAppointment,
} from "@/types/integration-appointment";

export function useIntegrationAppointments(
  status?: string,
  dateFrom?: string,
  dateTo?: string,
  skip: number = 0,
  limit: number = 20,
) {
  const params: Record<string, string> = { skip: String(skip), limit: String(limit) };
  if (status) params.status = status;
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;

  return useQuery({
    queryKey: ["admin", "integration", "appointments", status, dateFrom, dateTo, skip, limit] as const,
    queryFn: () => apiClient.get<AppointmentListResponse>("/api/admin/integrations/appointments", params),
    staleTime: 30 * 1000,
  });
}

export function useAppointmentStatusCounts() {
  return useQuery({
    queryKey: ["admin", "integration", "appointments", "counts"] as const,
    queryFn: () => apiClient.get<AppointmentStatusCounts>("/api/admin/integrations/appointments/counts"),
    staleTime: 30 * 1000,
  });
}

export function useAppointmentDetail(id: string | null) {
  return useQuery({
    queryKey: ["admin", "integration", "appointments", id] as const,
    queryFn: () => apiClient.get<IntegrationAppointment>(`/api/admin/integrations/appointments/${id}`),
    enabled: !!id,
  });
}

export function useUpdateAppointment() {
  const qc = useQueryClient();
  const t = useTranslations();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AppointmentUpdateRequest }) =>
      apiClient.put<IntegrationAppointment>(`/api/admin/integrations/appointments/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "integration", "appointments"] });
      toast.success(t("appointments.toast_updated"));
    },
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("appointments.toast_update_failed"));
    },
  });
}

export function useRetryAppointment() {
  const qc = useQueryClient();
  const t = useTranslations();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<IntegrationAppointment>(`/api/admin/integrations/appointments/${id}/retry`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "integration", "appointments"] });
      toast.success(t("appointments.toast_retried"));
    },
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("appointments.toast_retry_failed"));
    },
  });
}

export function useExportIntegrationAppointmentsCsv() {
  const t = useTranslations();
  return useMutation({
    mutationFn: async (params: { status?: string }) => {
      const queryParams: Record<string, string | undefined> = {};
      if (params.status) queryParams.status = params.status;

      const blob = await apiClient.getBlob(
        "/api/admin/integrations/appointments/export/csv",
        queryParams,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `integration_appointments_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    onSuccess: () => {
      toast.success(t("appointments.export_csv_success"));
    },
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("appointments.export_csv_error"));
    },
  });
}

export function useCancelAppointment() {
  const qc = useQueryClient();
  const t = useTranslations();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<IntegrationAppointment>(`/api/admin/integrations/appointments/${id}/cancel`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "integration", "appointments"] });
      toast.success(t("appointments.toast_cancelled"));
    },
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("appointments.toast_cancel_failed"));
    },
  });
}
