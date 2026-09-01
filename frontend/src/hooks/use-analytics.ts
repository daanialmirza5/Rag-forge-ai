import { useQuery } from "@tanstack/react-query";

import { getOrganizationUsage, getWorkspaceUsage } from "@/lib/api/analytics";

export function useWorkspaceUsage(workspaceId: string, lookbackDays = 30) {
  return useQuery({
    queryKey: ["workspace-usage", workspaceId, lookbackDays],
    queryFn: () => getWorkspaceUsage(workspaceId, lookbackDays),
  });
}

export function useOrganizationUsage(organizationId: string, lookbackDays = 30, enabled = true) {
  return useQuery({
    queryKey: ["organization-usage", organizationId, lookbackDays],
    queryFn: () => getOrganizationUsage(organizationId, lookbackDays),
    enabled,
  });
}
