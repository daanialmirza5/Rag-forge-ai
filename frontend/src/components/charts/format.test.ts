import { describe, expect, it } from "vitest";

import {
  eventTypeLabel,
  formatCompactCurrency,
  formatCompactNumber,
} from "@/components/charts/format";

// Pinned to en-US so assertions on compact notation (K/M vs. lakh/crore
// etc.) don't depend on the machine's default locale — production code
// still defaults to the viewer's own locale.
const LOCALE = "en-US";

describe("formatCompactNumber", () => {
  it("formats small numbers as-is", () => {
    expect(formatCompactNumber(42, LOCALE)).toBe("42");
  });

  it("compacts large numbers", () => {
    expect(formatCompactNumber(12_900, LOCALE)).toMatch(/^12\.9K$/);
  });
});

describe("formatCompactCurrency", () => {
  it("shows an exact zero", () => {
    expect(formatCompactCurrency(0, LOCALE)).toBe("$0");
  });

  it("floors tiny positive costs to a legible minimum", () => {
    expect(formatCompactCurrency(0.001, LOCALE)).toBe("<$0.01");
  });

  it("shows cents for everyday amounts", () => {
    expect(formatCompactCurrency(4.2, LOCALE)).toBe("$4.20");
  });

  it("compacts large amounts", () => {
    expect(formatCompactCurrency(4_200_000, LOCALE)).toMatch(/^\$4\.2M$/);
  });
});

describe("eventTypeLabel", () => {
  it("maps known event types to readable labels", () => {
    expect(eventTypeLabel("chat_message")).toBe("Chat messages");
    expect(eventTypeLabel("document_ingested")).toBe("Documents ingested");
  });

  it("falls back to the raw value for unknown event types", () => {
    expect(eventTypeLabel("some_new_event")).toBe("some_new_event");
  });
});
