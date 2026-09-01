import { Fragment } from "react";

import { CitationMarker } from "@/components/chat/citation-marker";
import type { ContextChunkPreview } from "@/types/api";

const CITATION_RE = /\[(\d+)\]/g;

/** Splits assistant text on `[n]` citation markers and renders each as an
 * interactive `CitationMarker`, looked up from a `marker_index -> chunk` map
 * built by the caller (see `use-chat.ts` / the conversation history page for
 * the two ways that map gets constructed). */
export function MessageContent({
  content,
  citationsByIndex,
}: {
  content: string;
  citationsByIndex?: Record<number, ContextChunkPreview>;
}) {
  if (!citationsByIndex || Object.keys(citationsByIndex).length === 0) {
    return <span className="whitespace-pre-wrap">{content}</span>;
  }

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  CITATION_RE.lastIndex = 0;

  while ((match = CITATION_RE.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(
        <span key={`text-${lastIndex}`} className="whitespace-pre-wrap">
          {content.slice(lastIndex, match.index)}
        </span>,
      );
    }
    const markerIndex = Number(match[1]);
    parts.push(
      <CitationMarker key={`cite-${match.index}`} index={markerIndex} chunk={citationsByIndex[markerIndex]} />,
    );
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < content.length) {
    parts.push(
      <span key={`text-${lastIndex}`} className="whitespace-pre-wrap">
        {content.slice(lastIndex)}
      </span>,
    );
  }

  return <Fragment>{parts}</Fragment>;
}
