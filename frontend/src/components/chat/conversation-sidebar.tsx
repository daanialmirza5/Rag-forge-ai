"use client";

import { MessageSquarePlus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useConversations, useDeleteConversation } from "@/hooks/use-conversations";
import { cn } from "@/lib/utils";

export function ConversationSidebar({
  workspaceId,
  activeConversationId,
}: {
  workspaceId: string;
  activeConversationId: string | null;
}) {
  const router = useRouter();
  const { data: conversations, isLoading } = useConversations(workspaceId);
  const deleteConversation = useDeleteConversation(workspaceId);

  return (
    <div className="flex h-screen w-64 shrink-0 flex-col border-r">
      <div className="p-3">
        <Button
          variant="outline"
          className="w-full justify-start gap-2"
          onClick={() => router.push(`/workspaces/${workspaceId}/chat`)}
        >
          <MessageSquarePlus className="h-4 w-4" /> New chat
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto px-2">
        {isLoading && <p className="p-2 text-xs text-muted-foreground">Loading…</p>}
        {conversations?.map((conversation) => (
          <div
            key={conversation.id}
            className={cn(
              "group flex items-center justify-between rounded-md px-2 py-1.5 text-sm hover:bg-accent",
              conversation.id === activeConversationId && "bg-accent",
            )}
          >
            <Link
              href={`/workspaces/${workspaceId}/chat/${conversation.id}`}
              className="min-w-0 flex-1 truncate"
            >
              {conversation.title}
            </Link>
            <button
              onClick={(e) => {
                e.preventDefault();
                deleteConversation.mutate(conversation.id);
                if (conversation.id === activeConversationId) {
                  router.push(`/workspaces/${workspaceId}/chat`);
                }
              }}
              className="ml-1 shrink-0 opacity-0 group-hover:opacity-100"
              aria-label="Delete conversation"
            >
              <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
            </button>
          </div>
        ))}
        {conversations?.length === 0 && (
          <p className="p-2 text-xs text-muted-foreground">No conversations yet.</p>
        )}
      </div>
    </div>
  );
}
