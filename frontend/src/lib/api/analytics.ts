import { apiFetch } from "@/lib/api/client";
import type { UsageSummary } from "@/types/api";

export function getWorkspaceUsage(
  workspaceId: string,
  lookbackDays = 30,
): Promise<UsageSummary> {
  return apiFetch<UsageSummary>(
    `/workspaces/${workspaceId}/analytics/usage?lookback_days=${lookbackDays}`,
  );
}

export function getOrganizationUsage(
  organizationId: string,
  lookbackDays = 30,
): Promise<UsageSummary> {
  return apiFetch<UsageSummary>(
    `/organizations/${organizationId}/analytics/usage?lookback_days=${lookbackDays}`,
  );
}
