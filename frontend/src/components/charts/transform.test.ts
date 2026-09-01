import { describe, expect, it } from "vitest";

import { buildDailySeries } from "@/components/charts/transform";
import type { UsageDailyPoint } from "@/types/api";

function toDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

describe("buildDailySeries", () => {
  it("zero-fills every day in the lookback window, not just days with data", () => {
    const result = buildDailySeries([], 7);
    expect(result.days).toHaveLength(7);
    expect(result.tokensInput).toEqual([0, 0, 0, 0, 0, 0, 0]);
    expect(result.eventSeries).toHaveLength(4);
    expect(result.eventSeries.every((s) => s.values.every((v) => v === 0))).toBe(true);
  });

  it("the last day in the window is today", () => {
    const result = buildDailySeries([], 30);
    expect(result.days.at(-1)).toBe(toDateKey(new Date()));
  });

  it("aggregates multiple event types on the same day without cross-contaminating", () => {
    const today = toDateKey(new Date());
    const points: UsageDailyPoint[] = [
      {
        day: today,
        event_type: "chat_message",
        event_count: 3,
        tokens_input: 100,
        tokens_output: 40,
        cost_usd: 0.01,
      },
      {
        day: today,
        event_type: "document_ingested",
        event_count: 1,
        tokens_input: 500,
        tokens_output: 0,
        cost_usd: 0,
      },
    ];
    const result = buildDailySeries(points, 7);

    expect(result.tokensInput.at(-1)).toBe(600);
    expect(result.tokensOutput.at(-1)).toBe(40);
    expect(result.cost.at(-1)).toBeCloseTo(0.01);

    const chatSeries = result.eventSeries.find((s) => s.eventType === "chat_message")!;
    const ingestSeries = result.eventSeries.find((s) => s.eventType === "document_ingested")!;
    expect(chatSeries.values.at(-1)).toBe(3);
    expect(ingestSeries.values.at(-1)).toBe(1);
  });

  it("drops points outside the requested window's zero-filled days", () => {
    const points: UsageDailyPoint[] = [
      {
        day: "2000-01-01",
        event_type: "chat_message",
        event_count: 5,
        tokens_input: 999,
        tokens_output: 999,
        cost_usd: 9,
      },
    ];
    const result = buildDailySeries(points, 7);
    expect(result.tokensInput.every((v) => v === 0)).toBe(true);
  });
});
