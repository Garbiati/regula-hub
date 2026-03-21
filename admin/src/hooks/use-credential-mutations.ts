import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/lib/api-error";
import { queryKeys } from "@/lib/query-keys";
import type { Credential, CredentialCreate, CredentialUpdate } from "@/types/credential";

export function useCreateCredential() {
  const qc = useQueryClient();
  const t = useTranslations();
  return useMutation({
    mutationFn: (data: CredentialCreate) => apiClient.post<Credential>("/api/admin/credentials", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.admin.credentials.all });
      toast.success(t("credentials.toast_created"));
    },
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("credentials.toast_create_failed"));
    },
  });
}

export function useUpdateCredential() {
  const qc = useQueryClient();
  const t = useTranslations();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CredentialUpdate }) =>
      apiClient.put<Credential>(`/api/admin/credentials/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.admin.credentials.all });
      toast.success(t("credentials.toast_updated"));
    },
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("credentials.toast_update_failed"));
    },
  });
}

export function useDeleteCredential() {
  const qc = useQueryClient();
  const t = useTranslations();
  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`/api/admin/credentials/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.admin.credentials.all });
      toast.success(t("credentials.toast_deleted"));
    },
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("credentials.toast_delete_failed"));
    },
  });
}
