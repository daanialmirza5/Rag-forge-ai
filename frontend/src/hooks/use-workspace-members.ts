import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { addWorkspaceMember, listWorkspaceMembers, removeWorkspaceMember } from "@/lib/api/workspaces";

export function useWorkspaceMembers(organizationId: string, workspaceId: string) {
  return useQuery({
    queryKey: ["workspace-members", workspaceId],
    queryFn: () => listWorkspaceMembers(organizationId, workspaceId),
  });
}

export function useAddWorkspaceMember(organizationId: string, workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { user_email: string; role: "owner" | "editor" | "viewer" }) =>
      addWorkspaceMember(organizationId, workspaceId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspace-members", workspaceId] });
    },
  });
}

export function useRemoveWorkspaceMember(organizationId: string, workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (memberId: string) => removeWorkspaceMember(organizationId, workspaceId, memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspace-members", workspaceId] });
    },
  });
}
