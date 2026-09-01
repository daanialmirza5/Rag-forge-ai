"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import type { ChatUIMessage } from "@/components/chat/chat-message";
import { getConversationMessages } from "@/lib/api/chat";
import { streamChat } from "@/lib/api/chat";
import { ApiError } from "@/lib/api/client";
import { toast } from "@/store/toast-store";
import type { ContextChunkPreview } from "@/types/api";

function citationsByIndexFromMessage(
  citations: { marker_index: number; document_id: string; document_filename: string; chunk_id: string; chunk_content: string; page_number: number | null; relevance_score: number }[],
): Record<number, ContextChunkPreview> {
  const map: Record<number, ContextChunkPreview> = {};
  for (const c of citations) {
    map[c.marker_index] = {
      chunk_id: c.chunk_id,
      document_id: c.document_id,
      document_filename: c.document_filename,
      content: c.chunk_content,
      page_number: c.page_number,
      relevance_score: c.relevance_score,
    };
  }
  return map;
}

export function useChat(workspaceId: string, initialConversationId: string | null) {
  const router = useRouter();
  const [conversationId, setConversationId] = useState(initialConversationId);
  const [messages, setMessages] = useState<ChatUIMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(!!initialConversationId);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!initialConversationId) {
      setMessages([]);
      setIsLoadingHistory(false);
      return;
    }
    setIsLoadingHistory(true);
    getConversationMessages(workspaceId, initialConversationId)
      .then((history) => {
        if (cancelled) return;
        setMessages(
          history.map((m) => ({
            id: m.id,
            role: m.role === "assistant" ? "assistant" : "user",
            content: m.content,
            citationsByIndex:
              m.citations.length > 0 ? citationsByIndexFromMessage(m.citations) : undefined,
          })),
        );
      })
      .catch(() => {
        if (!cancelled) toast({ title: "Could not load conversation", variant: "destructive" });
      })
      .finally(() => {
        if (!cancelled) setIsLoadingHistory(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, initialConversationId]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const sendMessage = useCallback(
    async (text: string) => {
      const userMessage: ChatUIMessage = { id: crypto.randomUUID(), role: "user", content: text };
      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        userMessage,
        { id: assistantId, role: "assistant", content: "", isStreaming: true },
      ]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        for await (const event of streamChat(
          workspaceId,
          { conversation_id: conversationId, message: text },
          { signal: controller.signal },
        )) {
          if (event.type === "token") {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + event.text } : m)),
            );
          } else if (event.type === "done") {
            const isNewConversation = !conversationId;
            setConversationId(event.conversation_id);
            const citationsByIndex: Record<number, ContextChunkPreview> = {};
            for (const idx of event.cited_indices) {
              const chunk = event.context_chunks[idx - 1];
              if (chunk) citationsByIndex[idx] = chunk;
            }
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, id: event.message_id, citationsByIndex, isStreaming: false }
                  : m,
              ),
            );
            if (isNewConversation) {
              router.replace(`/workspaces/${workspaceId}/chat/${event.conversation_id}`);
            }
          } else if (event.type === "error") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content || `_${event.message}_`, isStreaming: false }
                  : m,
              ),
            );
            toast({ title: "Response incomplete", description: event.message, variant: "destructive" });
          }
        }
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          const message = error instanceof ApiError ? error.message : "Chat request failed";
          toast({ title: "Something went wrong", description: message, variant: "destructive" });
          setMessages((prev) => prev.filter((m) => m.id !== assistantId || m.content));
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [workspaceId, conversationId, router],
  );

  return { messages, sendMessage, isStreaming, isLoadingHistory, conversationId };
}
