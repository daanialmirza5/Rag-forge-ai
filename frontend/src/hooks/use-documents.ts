import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  deleteDocument,
  getDocument,
  getIngestionStatus,
  listDocumentChunks,
  listDocuments,
  reingestDocument,
  uploadDocument,
} from "@/lib/api/documents";
import type { DocumentRecord } from "@/types/api";

const ACTIVE_STATUSES = new Set<DocumentRecord["status"]>(["pending", "processing"]);

export function useDocuments(workspaceId: string) {
  return useQuery({
    queryKey: ["documents", workspaceId],
    queryFn: () => listDocuments(workspaceId),
    // Poll while any document is still being ingested so status badges and
    // the eventual chunk count update without a manual refresh.
    refetchInterval: (query) => {
      const docs = query.state.data;
      return docs?.some((d) => ACTIVE_STATUSES.has(d.status)) ? 3000 : false;
    },
  });
}

export function useDocument(workspaceId: string, documentId: string) {
  return useQuery({
    queryKey: ["documents", workspaceId, documentId],
    queryFn: () => getDocument(workspaceId, documentId),
    refetchInterval: (query) =>
      query.state.data && ACTIVE_STATUSES.has(query.state.data.status) ? 3000 : false,
  });
}

export function useIngestionStatus(workspaceId: string, documentId: string) {
  return useQuery({
    queryKey: ["documents", workspaceId, documentId, "status"],
    queryFn: () => getIngestionStatus(workspaceId, documentId),
    refetchInterval: (query) =>
      query.state.data && (query.state.data.status === "pending" || query.state.data.status === "running")
        ? 3000
        : false,
  });
}

export function useDocumentChunks(workspaceId: string, documentId: string, enabled = true) {
  return useQuery({
    queryKey: ["documents", workspaceId, documentId, "chunks"],
    queryFn: () => listDocumentChunks(workspaceId, documentId),
    enabled,
  });
}

export function useUploadDocument(workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadDocument(workspaceId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] });
    },
  });
}

export function useDeleteDocument(workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => deleteDocument(workspaceId, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] });
    },
  });
}

export function useReingestDocument(workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => reingestDocument(workspaceId, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] });
    },
  });
}
