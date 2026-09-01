import type { UsageDailyPoint, UsageEventType } from "@/types/api";

const EVENT_TYPES: UsageEventType[] = [
  "chat_message",
  "document_ingested",
  "embedding_batch",
  "rerank_call",
];

function toDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** Fills in every day in the lookback window (zero-filled where the backend
 * has no rows) so the x-axis is a continuous timeline rather than only the
 * days that happened to have usage. */
export function buildDailySeries(points: UsageDailyPoint[], lookbackDays: number) {
  const today = new Date();
  const days: string[] = [];
  for (let i = lookbackDays - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    days.push(toDateKey(d));
  }

  const byDay = new Map<string, UsageDailyPoint[]>();
  for (const point of points) {
    const list = byDay.get(point.day) ?? [];
    list.push(point);
    byDay.set(point.day, list);
  }

  const tokensInput = days.map((day) => (byDay.get(day) ?? []).reduce((sum, p) => sum + p.tokens_input, 0));
  const tokensOutput = days.map((day) => (byDay.get(day) ?? []).reduce((sum, p) => sum + p.tokens_output, 0));
  const cost = days.map((day) => (byDay.get(day) ?? []).reduce((sum, p) => sum + p.cost_usd, 0));
  const eventSeries = EVENT_TYPES.map((eventType) => ({
    eventType,
    values: days.map((day) => (byDay.get(day) ?? []).find((p) => p.event_type === eventType)?.event_count ?? 0),
  }));

  return { days, tokensInput, tokensOutput, cost, eventSeries };
}
