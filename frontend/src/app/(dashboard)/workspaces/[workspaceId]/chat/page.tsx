"use client";

import { use } from "react";

import { ChatView } from "@/components/chat/chat-view";
import { ConversationSidebar } from "@/components/chat/conversation-sidebar";

export default function NewChatPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = use(params);

  return (
    <div className="flex">
      <ConversationSidebar workspaceId={workspaceId} activeConversationId={null} />
      <div className="flex-1">
        <ChatView workspaceId={workspaceId} conversationId={null} />
      </div>
    </div>
  );
}
