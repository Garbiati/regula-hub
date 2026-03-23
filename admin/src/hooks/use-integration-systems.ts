import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { IntegrationSystemListResponse } from "@/types/integration";

export function useIntegrationSystems() {
  return useQuery({
    queryKey: queryKeys.admin.integration.systems,
    queryFn: () => apiClient.get<IntegrationSystemListResponse>("/api/admin/integrations/systems"),
    staleTime: 5 * 60 * 1000,
  });
}
