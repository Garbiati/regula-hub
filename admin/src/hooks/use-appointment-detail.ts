"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { AppointmentDetail } from "@/types/appointment";

export function useAppointmentDetail(code: string | null, username: string, profileType: string) {
  return useQuery({
    queryKey: queryKeys.sisreg.detail(code ?? ""),
    queryFn: () =>
      apiClient.get<AppointmentDetail>(`/api/admin/sisreg/${code}/detail`, {
        username,
        profile_type: profileType,
      }),
    enabled: !!code && !!username,
    staleTime: 5 * 60 * 1000,
  });
}
