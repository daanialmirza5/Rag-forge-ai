import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deleteConversation, listConversations } from "@/lib/api/chat";
import { ApiError } from "@/lib/api/client";
import { toast } from "@/store/toast-store";

export function useConversations(workspaceId: string) {
  return useQuery({
    queryKey: ["conversations", workspaceId],
    queryFn: () => listConversations(workspaceId),
  });
}

export function useDeleteConversation(workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) => deleteConversation(workspaceId, conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations", workspaceId] });
    },
    onError: (error) => {
      const message =
        error instanceof ApiError && error.status === 403
          ? "You need editor access to delete conversations."
          : "Could not delete conversation.";
      toast({ title: message, variant: "destructive" });
    },
  });
}
