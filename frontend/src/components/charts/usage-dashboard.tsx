"use client";

import { useMemo } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DateRangeFilter } from "@/components/charts/date-range-filter";
import { eventTypeLabel, formatCompactCurrency, formatCompactNumber } from "@/components/charts/format";
import { LineChart } from "@/components/charts/line-chart";
import { StackedBarChart } from "@/components/charts/stacked-bar-chart";
import { StatTile } from "@/components/charts/stat-tile";
import { buildDailySeries } from "@/components/charts/transform";
import { UsageDataTable } from "@/components/charts/usage-data-table";
import type { UsageSummary } from "@/types/api";

// Refer to the CSS custom properties (globals.css) rather than resolved hex
// so marks stay correct across the light/dark theme toggle without any
// JS recomputation — the browser re-resolves var() at paint time.
const EVENT_TYPE_COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)"];

interface UsageDashboardProps {
  summary: UsageSummary | undefined;
  isLoading: boolean;
  lookbackDays: number;
  onLookbackDaysChange: (days: number) => void;
}

export function UsageDashboard({
  summary,
  isLoading,
  lookbackDays,
  onLookbackDaysChange,
}: UsageDashboardProps) {
  const daily = useMemo(
    () => buildDailySeries(summary?.points ?? [], lookbackDays),
    [summary, lookbackDays],
  );

  return (
    <div className="flex flex-col gap-6">
      <DateRangeFilter value={lookbackDays} onChange={onLookbackDaysChange} />

      <div
        className="grid grid-cols-2 gap-3 transition-opacity md:grid-cols-4"
        style={{ opacity: isLoading ? 0.6 : 1 }}
      >
        <StatTile label="Total events" value={formatCompactNumber(summary?.total_events ?? 0)} />
        <StatTile label="Input tokens" value={formatCompactNumber(summary?.total_tokens_input ?? 0)} />
        <StatTile label="Output tokens" value={formatCompactNumber(summary?.total_tokens_output ?? 0)} />
        <StatTile label="Estimated cost" value={formatCompactCurrency(summary?.total_cost_usd ?? 0)} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2" style={{ opacity: isLoading ? 0.6 : 1 }}>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Token usage</CardTitle>
          </CardHeader>
          <CardContent>
            <LineChart
              days={daily.days}
              series={[
                { id: "input", label: "Input tokens", color: EVENT_TYPE_COLORS[0]!, values: daily.tokensInput },
                { id: "output", label: "Output tokens", color: EVENT_TYPE_COLORS[1]!, values: daily.tokensOutput },
              ]}
              valueFormatter={formatCompactNumber}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Estimated LLM cost</CardTitle>
          </CardHeader>
          <CardContent>
            <LineChart
              days={daily.days}
              series={[{ id: "cost", label: "Cost", color: EVENT_TYPE_COLORS[0]!, values: daily.cost }]}
              valueFormatter={formatCompactCurrency}
            />
          </CardContent>
        </Card>
      </div>

      <Card style={{ opacity: isLoading ? 0.6 : 1 }}>
        <CardHeader>
          <CardTitle className="text-base">Events by type</CardTitle>
        </CardHeader>
        <CardContent>
          <StackedBarChart
            days={daily.days}
            series={daily.eventSeries.map((s, i) => ({
              id: s.eventType,
              label: eventTypeLabel(s.eventType),
              color: EVENT_TYPE_COLORS[i] ?? EVENT_TYPE_COLORS[0]!,
              values: s.values,
            }))}
            valueFormatter={formatCompactNumber}
          />
        </CardContent>
      </Card>

      <UsageDataTable points={summary?.points ?? []} />
    </div>
  );
}
