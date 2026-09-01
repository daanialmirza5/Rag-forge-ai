"use client";

import { AlertCircle, FileText, MoreVertical, RefreshCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { DocumentStatusBadge } from "@/components/documents/document-status-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDeleteDocument, useDocuments, useReingestDocument } from "@/hooks/use-documents";
import { formatBytes, formatDate } from "@/lib/utils";
import { toast } from "@/store/toast-store";

export function DocumentList({ workspaceId }: { workspaceId: string }) {
  const { data: documents, isLoading } = useDocuments(workspaceId);
  const deleteDocument = useDeleteDocument(workspaceId);
  const reingestDocument = useReingestDocument(workspaceId);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading documents…</p>;
  }

  if (!documents || documents.length === 0) {
    return (
      <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
        No documents yet. Upload one to start asking questions about it.
      </p>
    );
  }

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) => (prev.size === documents!.length ? new Set() : new Set(documents!.map((d) => d.id))));
  }

  async function handleBulkDelete() {
    setBulkDeleting(true);
    const ids = Array.from(selected);
    const results = await Promise.allSettled(ids.map((id) => deleteDocument.mutateAsync(id)));
    const failures = results.filter((r) => r.status === "rejected").length;
    setBulkDeleting(false);
    setSelected(new Set());
    if (failures > 0) {
      toast({
        title: `Deleted ${ids.length - failures} of ${ids.length} documents`,
        description: `${failures} could not be deleted.`,
        variant: "destructive",
      });
    } else {
      toast({ title: `Deleted ${ids.length} document${ids.length === 1 ? "" : "s"}` });
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3 px-1">
        <input
          type="checkbox"
          className="h-4 w-4 rounded border-input"
          checked={selected.size > 0 && selected.size === documents.length}
          ref={(el) => {
            if (el) el.indeterminate = selected.size > 0 && selected.size < documents.length;
          }}
          onChange={toggleAll}
          aria-label="Select all documents"
        />
        {selected.size > 0 ? (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">{selected.size} selected</span>
            <Button
              size="sm"
              variant="destructive"
              disabled={bulkDeleting}
              onClick={handleBulkDelete}
            >
              Delete selected
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>
              Clear
            </Button>
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">Select all</span>
        )}
      </div>

      <div className="divide-y rounded-lg border">
        {documents.map((doc) => (
          <div key={doc.id} className="flex items-center gap-3 p-3">
            <input
              type="checkbox"
              className="h-4 w-4 shrink-0 rounded border-input"
              checked={selected.has(doc.id)}
              onChange={() => toggleOne(doc.id)}
              aria-label={`Select ${doc.original_filename}`}
            />
            <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
            <Link
              href={`/workspaces/${workspaceId}/documents/${doc.id}`}
              className="min-w-0 flex-1 hover:underline"
            >
              <p className="truncate text-sm font-medium">{doc.original_filename}</p>
              <p className="text-xs text-muted-foreground">
                {formatBytes(doc.size_bytes)} · Uploaded {formatDate(doc.created_at)}
              </p>
              {doc.status === "failed" && doc.error_message && (
                <p className="mt-1 flex items-center gap-1 text-xs text-destructive">
                  <AlertCircle className="h-3 w-3" /> {doc.error_message}
                </p>
              )}
            </Link>
            <DocumentStatusBadge status={doc.status} />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onSelect={async () => {
                    try {
                      await reingestDocument.mutateAsync(doc.id);
                      toast({ title: "Re-ingestion started" });
                    } catch {
                      toast({ title: "Could not re-ingest document", variant: "destructive" });
                    }
                  }}
                  className="gap-2"
                >
                  <RefreshCw className="h-4 w-4" /> Re-ingest
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={async () => {
                    try {
                      await deleteDocument.mutateAsync(doc.id);
                      toast({ title: "Document deleted" });
                    } catch {
                      toast({ title: "Could not delete document", variant: "destructive" });
                    }
                  }}
                  className="gap-2 text-destructive"
                >
                  <Trash2 className="h-4 w-4" /> Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ))}
      </div>
    </div>
  );
}
