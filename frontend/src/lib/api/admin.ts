import { apiFetch } from "@/lib/api/client";
import type { AdminAuditLog, AdminOrganization, AdminUser, Paginated, UsageSummary } from "@/types/api";

export function listAdminOrganizations(): Promise<AdminOrganization[]> {
  return apiFetch<AdminOrganization[]>("/admin/organizations");
}

export function updateOrganizationPlan(
  organizationId: string,
  planTier: string,
): Promise<AdminOrganization> {
  return apiFetch<AdminOrganization>(`/admin/organizations/${organizationId}/plan`, {
    method: "PATCH",
    body: { plan_tier: planTier },
  });
}

export function listAdminUsers(): Promise<AdminUser[]> {
  return apiFetch<AdminUser[]>("/admin/users");
}

export function updateUserActive(userId: string, isActive: boolean): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/admin/users/${userId}/active`, {
    method: "PATCH",
    body: { is_active: isActive },
  });
}

export function updateUserSuperuser(userId: string, isSuperuser: boolean): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/admin/users/${userId}/superuser`, {
    method: "PATCH",
    body: { is_superuser: isSuperuser },
  });
}

export function getPlatformUsage(lookbackDays = 30): Promise<UsageSummary> {
  return apiFetch<UsageSummary>(`/admin/usage?lookback_days=${lookbackDays}`);
}

export function listAuditLogs(page = 1, pageSize = 50): Promise<Paginated<AdminAuditLog>> {
  return apiFetch<Paginated<AdminAuditLog>>(
    `/admin/audit-logs?page=${page}&page_size=${pageSize}`,
  );
}
