import { useMutation } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import type { ValidateLoginResult } from "@/types/credential";

export function useValidateLogin() {
  return useMutation({
    mutationFn: (data: { username: string; password: string }) =>
      apiClient.post<ValidateLoginResult>("/api/admin/credentials/validate-login", data),
  });
}
