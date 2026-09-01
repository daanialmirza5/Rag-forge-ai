"use client";

import { use } from "react";

import { ChatView } from "@/components/chat/chat-view";
import { ConversationSidebar } from "@/components/chat/conversation-sidebar";

export default function ConversationPage({
  params,
}: {
  params: Promise<{ workspaceId: string; conversationId: string }>;
}) {
  const { workspaceId, conversationId } = use(params);

  return (
    <div className="flex">
      <ConversationSidebar workspaceId={workspaceId} activeConversationId={conversationId} />
      <div className="flex-1">
        <ChatView workspaceId={workspaceId} conversationId={conversationId} />
      </div>
    </div>
  );
}
