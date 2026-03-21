import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { UpsertSelectionRequest, UserSelection, UserSelectionListResponse } from "@/types/user";

export function useUserSelections(userId: string | null) {
  return useQuery({
    queryKey: queryKeys.admin.users.selections(userId ?? ""),
    queryFn: async () => {
      const data = await apiClient.get<UserSelectionListResponse>(`/api/admin/users/${userId}/selections`);
      return data.items;
    },
    staleTime: 5 * 60 * 1000,
    enabled: !!userId,
  });
}

export function useUpsertSelection(userId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (body: UpsertSelectionRequest) => {
      return apiClient.put<UserSelection>(`/api/admin/users/${userId}/selections`, body);
    },
    onSuccess: () => {
      if (userId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.admin.users.selections(userId) });
      }
    },
  });
}
