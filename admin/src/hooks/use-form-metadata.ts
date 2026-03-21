import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { FormMetadata } from "@/types/form-metadata";

export function useFormMetadata(systemCode: string, endpointName: string) {
  return useQuery({
    queryKey: queryKeys.admin.formMetadata(systemCode, endpointName),
    queryFn: () =>
      apiClient.get<FormMetadata>(`/api/admin/regulation-systems/${systemCode}/form-metadata/${endpointName}`),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: 1,
  });
}
