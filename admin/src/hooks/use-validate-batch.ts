import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { CredentialValidation } from "@/types/credential";

export function useValidateBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ system, profileType }: { system: string; profileType: string }) =>
      apiClient.post<CredentialValidation[]>(
        `/api/admin/credentials/validate-batch?system=${encodeURIComponent(system)}&profile_type=${encodeURIComponent(profileType)}`,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.admin.credentials.all });
    },
  });
}
