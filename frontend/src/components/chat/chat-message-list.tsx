"use client";

import { useEffect, useRef } from "react";

import { ChatMessageBubble, type ChatUIMessage } from "@/components/chat/chat-message";

export function ChatMessageList({ messages }: { messages: ChatUIMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-center">
        <div>
          <p className="text-lg font-medium">Ask anything about your documents</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Answers are grounded in your uploaded documents and cite their sources.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
      {messages.map((message) => (
        <ChatMessageBubble key={message.id} message={message} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
