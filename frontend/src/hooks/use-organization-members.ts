import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listOrganizationMembers, removeOrganizationMember } from "@/lib/api/organizations";

export function useOrganizationMembers(organizationId: string) {
  return useQuery({
    queryKey: ["organization-members", organizationId],
    queryFn: () => listOrganizationMembers(organizationId),
  });
}

export function useRemoveOrganizationMember(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (memberId: string) => removeOrganizationMember(organizationId, memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organization-members", organizationId] });
    },
  });
}
