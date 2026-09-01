"use client";

import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { useChat } from "@/hooks/use-chat";

export function ChatView({
  workspaceId,
  conversationId,
}: {
  workspaceId: string;
  conversationId: string | null;
}) {
  const { messages, sendMessage, isStreaming, isLoadingHistory } = useChat(
    workspaceId,
    conversationId,
  );

  if (isLoadingHistory) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">
        Loading conversation…
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <ChatMessageList messages={messages} />
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
