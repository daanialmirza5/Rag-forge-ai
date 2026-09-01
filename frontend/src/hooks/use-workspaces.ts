import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createWorkspace, listWorkspaces } from "@/lib/api/workspaces";

export function useWorkspaces(organizationId: string | null) {
  return useQuery({
    queryKey: ["workspaces", organizationId],
    queryFn: () => listWorkspaces(organizationId as string),
    enabled: !!organizationId,
  });
}

export function useCreateWorkspace(organizationId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; description?: string }) =>
      createWorkspace(organizationId as string, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspaces", organizationId] });
    },
  });
}
