import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/lib/api-error";
import { queryKeys } from "@/lib/query-keys";
import type { IntegrationExecution, TriggerExecutionRequest } from "@/types/integration";

export function useTriggerIntegration() {
  const qc = useQueryClient();
  const t = useTranslations();
  return useMutation({
    mutationFn: (data: TriggerExecutionRequest) =>
      apiClient.post<IntegrationExecution>("/api/admin/integrations/execute", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.admin.integration.executions() });
      toast.success(t("integrations.toast_triggered"));
    },
    onError: (err) => {
      const detail = err instanceof ApiError ? err.detail : undefined;
      toast.error(detail ?? t("integrations.toast_trigger_failed"));
    },
  });
}
