import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { ExecutionListResponse } from "@/types/integration";

export function useIntegrationHistory(skip: number = 0, limit: number = 10, systemCode?: string) {
  const params: Record<string, string> = { skip: String(skip), limit: String(limit) };
  if (systemCode) params.system_code = systemCode;

  return useQuery({
    queryKey: queryKeys.admin.integration.executions(skip, limit),
    queryFn: () => apiClient.get<ExecutionListResponse>("/api/admin/integrations/executions", params),
    staleTime: 30 * 1000,
  });
}
