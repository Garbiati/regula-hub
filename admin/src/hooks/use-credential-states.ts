import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { CredentialState } from "@/types/credential";

export function useCredentialStates(system: string) {
  return useQuery({
    queryKey: queryKeys.admin.credentials.states(system),
    queryFn: () => apiClient.get<CredentialState[]>("/api/admin/credentials/states", { system }),
    staleTime: 5 * 60 * 1000,
  });
}
