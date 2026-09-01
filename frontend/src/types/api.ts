// Mirrors backend/app/schemas/*.py. Keep in sync manually — see
// docs/PROGRESS.md for the note on generating this from the OpenAPI schema
// as a future improvement.

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  email_verified: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan_tier: string;
}

export interface OrganizationMember {
  id: string;
  user_id: string;
  user_email: string;
  user_full_name: string;
  role: "owner" | "admin" | "member";
}

export interface Workspace {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string;
}

export interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user_id: string;
  user_email: string;
  user_full_name: string;
  role: "owner" | "editor" | "viewer";
}

export type DocumentStatus = "pending" | "processing" | "completed" | "failed";

export interface DocumentRecord {
  id: string;
  workspace_id: string;
  filename: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  page_number: number | null;
}

export interface IngestionJob {
  id: string;
  document_id: string;
  status: "pending" | "running" | "completed" | "failed";
  stage: string;
  error_message: string | null;
}

export interface DocumentUploadResponse {
  document: DocumentRecord;
  ingestion_job_id: string;
}

export interface Conversation {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  marker_index: number;
  document_id: string;
  document_filename: string;
  chunk_id: string;
  chunk_content: string;
  page_number: number | null;
  relevance_score: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  model_used: string | null;
  created_at: string;
  citations: Citation[];
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

// --- SSE chat stream event shapes (see app/services/chat_service.py) ---

export interface ContextChunkPreview {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  content: string;
  page_number: number | null;
  relevance_score: number;
}

export type ChatStreamEvent =
  | { type: "token"; text: string }
  | {
      type: "done";
      message_id: string;
      conversation_id: string;
      context_chunks: ContextChunkPreview[];
      cited_indices: number[];
    }
  | { type: "error"; message: string };

// --- Analytics (see app/schemas/analytics.py) ---

export type UsageEventType =
  | "chat_message"
  | "document_ingested"
  | "embedding_batch"
  | "rerank_call";

export interface UsageDailyPoint {
  day: string;
  event_type: UsageEventType;
  event_count: number;
  tokens_input: number;
  tokens_output: number;
  cost_usd: number;
}

export interface UsageSummary {
  points: UsageDailyPoint[];
  total_events: number;
  total_tokens_input: number;
  total_tokens_output: number;
  total_cost_usd: number;
}

// --- Admin panel (see app/schemas/admin.py) ---

export interface AdminOrganization {
  id: string;
  name: string;
  slug: string;
  plan_tier: string;
  member_count: number;
  workspace_count: number;
  created_at: string;
}

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  email_verified: boolean;
  created_at: string;
}

export interface AdminAuditLog {
  id: string;
  organization_id: string | null;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
