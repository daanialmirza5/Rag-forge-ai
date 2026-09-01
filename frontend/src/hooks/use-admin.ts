import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getPlatformUsage,
  listAdminOrganizations,
  listAdminUsers,
  listAuditLogs,
  updateOrganizationPlan,
  updateUserActive,
  updateUserSuperuser,
} from "@/lib/api/admin";

export function useAdminOrganizations() {
  return useQuery({ queryKey: ["admin-organizations"], queryFn: listAdminOrganizations });
}

export function useUpdateOrganizationPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ organizationId, planTier }: { organizationId: string; planTier: string }) =>
      updateOrganizationPlan(organizationId, planTier),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-organizations"] });
    },
  });
}

export function useAdminUsers() {
  return useQuery({ queryKey: ["admin-users"], queryFn: listAdminUsers });
}

export function useUpdateUserActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      updateUserActive(userId, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

export function useUpdateUserSuperuser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, isSuperuser }: { userId: string; isSuperuser: boolean }) =>
      updateUserSuperuser(userId, isSuperuser),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

export function usePlatformUsage(lookbackDays = 30) {
  return useQuery({
    queryKey: ["platform-usage", lookbackDays],
    queryFn: () => getPlatformUsage(lookbackDays),
  });
}

export function useAuditLogs(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: ["audit-logs", page, pageSize],
    queryFn: () => listAuditLogs(page, pageSize),
  });
}
