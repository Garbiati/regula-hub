import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { UserListResponse } from "@/types/user";

export function useUsers() {
  return useQuery({
    queryKey: queryKeys.admin.users.all,
    queryFn: async () => {
      const data = await apiClient.get<UserListResponse>("/api/admin/users");
      return data.items;
    },
    staleTime: 10 * 60 * 1000,
  });
}
