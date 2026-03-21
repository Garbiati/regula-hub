import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { CredentialListResponse } from "@/types/credential";

export function useCredentials(system: string) {
  return useQuery({
    queryKey: queryKeys.admin.credentials.list(system),
    queryFn: () => apiClient.get<CredentialListResponse>("/api/admin/credentials", { system }),
    staleTime: 5 * 60 * 1000,
  });
}
