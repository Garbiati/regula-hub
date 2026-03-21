import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { CredentialProfile } from "@/types/credential";
import { useProfileStore } from "@/stores/profile-store";

export function useAvailableProfiles() {
  const system = useProfileStore((s) => s.system);

  return useQuery({
    queryKey: queryKeys.admin.credentials.profiles(system),
    queryFn: async () => {
      const data = await apiClient.get<CredentialProfile[]>("/api/admin/credentials/profiles", {
        system,
      });
      return data.map((p) => p.name);
    },
    staleTime: 5 * 60 * 1000,
  });
}
