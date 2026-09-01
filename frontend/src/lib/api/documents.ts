import { apiFetch } from "@/lib/api/client";
import type { DocumentChunk, DocumentRecord, DocumentUploadResponse, IngestionJob } from "@/types/api";

export function listDocuments(workspaceId: string): Promise<DocumentRecord[]> {
  return apiFetch<DocumentRecord[]>(`/workspaces/${workspaceId}/documents`);
}

export function getDocument(workspaceId: string, documentId: string): Promise<DocumentRecord> {
  return apiFetch<DocumentRecord>(`/workspaces/${workspaceId}/documents/${documentId}`);
}

export function getIngestionStatus(
  workspaceId: string,
  documentId: string,
): Promise<IngestionJob | null> {
  return apiFetch<IngestionJob | null>(`/workspaces/${workspaceId}/documents/${documentId}/status`);
}

export function listDocumentChunks(
  workspaceId: string,
  documentId: string,
): Promise<DocumentChunk[]> {
  return apiFetch<DocumentChunk[]>(`/workspaces/${workspaceId}/documents/${documentId}/chunks`);
}

export function uploadDocument(workspaceId: string, file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<DocumentUploadResponse>(`/workspaces/${workspaceId}/documents`, {
    method: "POST",
    body: formData,
    isFormData: true,
  });
}

export function reingestDocument(workspaceId: string, documentId: string): Promise<IngestionJob> {
  return apiFetch<IngestionJob>(`/workspaces/${workspaceId}/documents/${documentId}/reingest`, {
    method: "POST",
  });
}

export function deleteDocument(workspaceId: string, documentId: string): Promise<void> {
  return apiFetch<void>(`/workspaces/${workspaceId}/documents/${documentId}`, {
    method: "DELETE",
  });
}
