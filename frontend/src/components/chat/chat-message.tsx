import { Bot, User } from "lucide-react";

import { MessageContent } from "@/components/chat/message-content";
import { cn } from "@/lib/utils";
import type { ContextChunkPreview } from "@/types/api";

export interface ChatUIMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citationsByIndex?: Record<number, ContextChunkPreview>;
  isStreaming?: boolean;
}

export function ChatMessageBubble({ message }: { message: ChatUIMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={cn(
          "max-w-[75%] rounded-lg px-4 py-2.5 text-sm leading-relaxed",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted",
        )}
      >
        {message.content ? (
          <MessageContent content={message.content} citationsByIndex={message.citationsByIndex} />
        ) : message.isStreaming ? (
          <span className="inline-flex gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" />
          </span>
        ) : null}
      </div>
    </div>
  );
}
