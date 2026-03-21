import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { RegulationSystemListResponse } from "@/types/regulation-system";

export function useRegulationSystems() {
  return useQuery({
    queryKey: queryKeys.admin.regulationSystems.list,
    queryFn: () => apiClient.get<RegulationSystemListResponse>("/api/admin/regulation-systems"),
    staleTime: 10 * 60 * 1000,
  });
}
