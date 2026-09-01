import { API_BASE_URL, ApiError, apiFetch, getValidAccessToken } from "@/lib/api/client";
import type { ChatStreamEvent, Conversation, Message } from "@/types/api";

export function listConversations(workspaceId: string): Promise<Conversation[]> {
  return apiFetch<Conversation[]>(`/workspaces/${workspaceId}/conversations`);
}

export function getConversationMessages(
  workspaceId: string,
  conversationId: string,
): Promise<Message[]> {
  return apiFetch<Message[]>(`/workspaces/${workspaceId}/conversations/${conversationId}`);
}

export function deleteConversation(workspaceId: string, conversationId: string): Promise<void> {
  return apiFetch<void>(`/workspaces/${workspaceId}/conversations/${conversationId}`, {
    method: "DELETE",
  });
}

/** Streams a chat turn via Server-Sent Events. The browser's native
 * `EventSource` can't do POST-with-body, so this parses the
 * `data: {...}\n\n` wire format manually off a `fetch()` ReadableStream. */
export async function* streamChat(
  workspaceId: string,
  payload: { conversation_id?: string | null; message: string },
  options?: { signal?: AbortSignal },
): AsyncGenerator<ChatStreamEvent, void, unknown> {
  const token = await getValidAccessToken();
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces/${workspaceId}/conversations/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal: options?.signal,
  });

  if (!res.ok || !res.body) {
    let code = "unknown_error";
    let message = "Chat request failed";
    try {
      const body = await res.json();
      code = body?.error?.code ?? code;
      message = body?.error?.message ?? message;
    } catch {
      // response body wasn't JSON — fall back to the defaults above
    }
    throw new ApiError(res.status, code, message);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data: "));
      if (dataLine) {
        yield JSON.parse(dataLine.slice("data: ".length)) as ChatStreamEvent;
      }
      boundary = buffer.indexOf("\n\n");
    }
  }
}
