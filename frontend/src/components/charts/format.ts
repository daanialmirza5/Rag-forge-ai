// `locale` defaults to the viewer's own locale (correct UX — respects their
// browser/OS setting) but can be pinned explicitly, which tests do to stay
// deterministic across CI runners with different default locales (e.g. a
// runner whose locale formats large numbers in lakhs instead of K/M/B).
export function formatCompactNumber(value: number, locale?: string): string {
  return new Intl.NumberFormat(locale, { notation: "compact", maximumFractionDigits: 1 }).format(
    value,
  );
}

export function formatCompactCurrency(value: number, locale?: string): string {
  if (value === 0) return "$0";
  if (value < 0.01) return "<$0.01";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "USD",
    notation: value >= 1000 ? "compact" : "standard",
    maximumFractionDigits: value >= 1000 ? 1 : 2,
  }).format(value);
}

export function formatShortDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export const EVENT_TYPE_LABELS: Record<string, string> = {
  chat_message: "Chat messages",
  document_ingested: "Documents ingested",
  embedding_batch: "Embedding batches",
  rerank_call: "Rerank calls",
};

export function eventTypeLabel(eventType: string): string {
  return EVENT_TYPE_LABELS[eventType] ?? eventType;
}
