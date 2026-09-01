"use client";

import { use } from "react";

import { DocumentList } from "@/components/documents/document-list";
import { DocumentUploadDropzone } from "@/components/documents/document-upload-dropzone";

export default function DocumentsPage({
  params,
}: {
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = use(params);

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-8">
      <div>
        <h1 className="text-xl font-semibold">Documents</h1>
        <p className="text-sm text-muted-foreground">
          Upload documents to make them searchable in chat.
        </p>
      </div>
      <DocumentUploadDropzone workspaceId={workspaceId} />
      <DocumentList workspaceId={workspaceId} />
    </div>
  );
}
