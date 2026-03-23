import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { IntegrationExecution } from "@/types/integration";

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

export function useIntegrationStatus(executionId: string | null) {
  return useQuery({
    queryKey: queryKeys.admin.integration.status(executionId ?? ""),
    queryFn: () =>
      apiClient.get<IntegrationExecution>(`/api/admin/integrations/executions/${executionId}/status`),
    enabled: !!executionId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && TERMINAL_STATUSES.has(status)) return false;
      return 2000;
    },
  });
}
