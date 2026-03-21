import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { CredentialListResponse } from "@/types/credential";
import { useProfileStore } from "@/stores/profile-store";

export function useProfileUsers() {
  const system = useProfileStore((s) => s.system);
  const profile = useProfileStore((s) => s.profile);

  return useQuery({
    queryKey: queryKeys.admin.credentials.byProfile(system, profile),
    queryFn: async () => {
      const data = await apiClient.get<CredentialListResponse>("/api/admin/credentials", {
        system,
        profile_type: profile,
      });
      return data.items;
    },
    staleTime: 5 * 60 * 1000,
    enabled: !!system && !!profile,
  });
}
