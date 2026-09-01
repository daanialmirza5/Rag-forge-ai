"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { ContextChunkPreview } from "@/types/api";

export function CitationMarker({ index, chunk }: { index: number; chunk?: ContextChunkPreview }) {
  if (!chunk) {
    // Model cited a number outside the retrieved set (shouldn't happen given
    // the prompt instructions, but render plainly rather than breaking).
    return <sup className="text-muted-foreground">[{index}]</sup>;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="mx-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded bg-primary/10 px-1 align-super text-[10px] font-semibold text-primary hover:bg-primary/20"
        >
          {index}
        </button>
      </TooltipTrigger>
      <TooltipContent side="top">
        <p className="font-medium">
          {chunk.document_filename}
          {chunk.page_number ? `, page ${chunk.page_number}` : ""}
        </p>
        <p className="mt-1 line-clamp-4 text-muted-foreground">{chunk.content}</p>
      </TooltipContent>
    </Tooltip>
  );
}
