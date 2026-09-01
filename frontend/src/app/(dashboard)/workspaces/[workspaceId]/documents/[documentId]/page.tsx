"use client";

import { AlertCircle, ArrowLeft, FileText } from "lucide-react";
import Link from "next/link";
import { use } from "react";

import { DocumentStatusBadge } from "@/components/documents/document-status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDocument, useDocumentChunks, useIngestionStatus } from "@/hooks/use-documents";
import { formatBytes, formatDate } from "@/lib/utils";

export default function DocumentDetailPage({
  params,
}: {
  params: Promise<{ workspaceId: string; documentId: string }>;
}) {
  const { workspaceId, documentId } = use(params);
  const { data: document, isLoading: documentLoading } = useDocument(workspaceId, documentId);
  const { data: job } = useIngestionStatus(workspaceId, documentId);
  const { data: chunks, isLoading: chunksLoading } = useDocumentChunks(
    workspaceId,
    documentId,
    document?.status === "completed",
  );

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-8">
      <Link
        href={`/workspaces/${workspaceId}/documents`}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to documents
      </Link>

      {documentLoading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {document && (
        <>
          <div className="flex items-start gap-3">
            <FileText className="mt-1 h-6 w-6 shrink-0 text-muted-foreground" />
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-xl font-semibold">{document.original_filename}</h1>
              <p className="text-sm text-muted-foreground">
                {formatBytes(document.size_bytes)} · {document.mime_type} · Uploaded{" "}
                {formatDate(document.created_at)}
              </p>
            </div>
            <DocumentStatusBadge status={document.status} />
          </div>

          {document.status === "failed" && document.error_message && (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {document.error_message}
            </div>
          )}

          {(document.status === "pending" || document.status === "processing") && (
            <div className="rounded-lg border p-4 text-sm text-muted-foreground">
              {job ? `Processing — ${job.stage.replace(/_/g, " ")}…` : "Queued for processing…"}
            </div>
          )}

          {document.status === "completed" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Chunks{chunks ? ` (${chunks.length})` : ""}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {chunksLoading && <p className="text-sm text-muted-foreground">Loading chunks…</p>}
                {chunks?.length === 0 && (
                  <p className="text-sm text-muted-foreground">No chunks were produced.</p>
                )}
                {chunks?.map((chunk) => (
                  <div key={chunk.id} className="rounded-md border p-3">
                    <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                      <Badge variant="outline">Chunk {chunk.chunk_index + 1}</Badge>
                      {chunk.page_number !== null && (
                        <Badge variant="outline">Page {chunk.page_number}</Badge>
                      )}
                      <span>{chunk.token_count} tokens</span>
                    </div>
                    <p className="max-h-48 overflow-y-auto whitespace-pre-wrap text-sm text-foreground">
                      {chunk.content}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
