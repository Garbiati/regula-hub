import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { CredentialValidation } from "@/types/credential";

export function useValidateCredential() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (credentialId: string) =>
      apiClient.post<CredentialValidation>(`/api/admin/credentials/${credentialId}/validate`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.admin.credentials.all });
    },
  });
}
