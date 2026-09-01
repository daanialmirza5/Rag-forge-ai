"use client";

import { Upload } from "lucide-react";
import { useRef, useState } from "react";

import { useUploadDocument } from "@/hooks/use-documents";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import { toast } from "@/store/toast-store";

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/html",
  "text/markdown",
  "text/plain",
];

export function DocumentUploadDropzone({ workspaceId }: { workspaceId: string }) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadDocument(workspaceId);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    for (const file of Array.from(files)) {
      try {
        await upload.mutateAsync(file);
        toast({ title: `${file.name} uploaded`, description: "Processing has started." });
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "Upload failed";
        toast({ title: `Could not upload ${file.name}`, description: message, variant: "destructive" });
      }
    }
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        void handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
        isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:bg-accent/50",
      )}
    >
      <Upload className="h-8 w-8 text-muted-foreground" />
      <p className="text-sm font-medium">Drop files here or click to upload</p>
      <p className="text-xs text-muted-foreground">PDF, DOCX, HTML, Markdown, or plain text</p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED_TYPES.join(",")}
        className="hidden"
        onChange={(e) => void handleFiles(e.target.files)}
      />
    </div>
  );
}
