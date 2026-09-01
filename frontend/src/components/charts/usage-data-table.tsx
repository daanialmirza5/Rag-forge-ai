import { eventTypeLabel, formatCompactCurrency } from "@/components/charts/format";
import type { UsageDailyPoint } from "@/types/api";

/** The accessible, non-visual twin of every chart on the page — same
 * underlying `points` data, so nothing shown in a chart is chart-only. */
export function UsageDataTable({ points }: { points: UsageDailyPoint[] }) {
  const sorted = [...points].sort((a, b) => a.day.localeCompare(b.day));

  return (
    <details className="rounded-lg border">
      <summary className="cursor-pointer select-none px-4 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground">
        View as table
      </summary>
      <div className="max-h-80 overflow-auto border-t">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-card text-xs text-muted-foreground">
            <tr>
              <th className="px-4 py-2 font-medium">Date</th>
              <th className="px-4 py-2 font-medium">Event type</th>
              <th className="px-4 py-2 font-medium tabular-nums">Events</th>
              <th className="px-4 py-2 font-medium tabular-nums">Input tokens</th>
              <th className="px-4 py-2 font-medium tabular-nums">Output tokens</th>
              <th className="px-4 py-2 font-medium tabular-nums">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {sorted.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-muted-foreground">
                  No usage recorded in this period.
                </td>
              </tr>
            )}
            {sorted.map((point) => (
              <tr key={`${point.day}-${point.event_type}`}>
                <td className="px-4 py-2 tabular-nums">{point.day}</td>
                <td className="px-4 py-2">{eventTypeLabel(point.event_type)}</td>
                <td className="px-4 py-2 tabular-nums">{point.event_count.toLocaleString()}</td>
                <td className="px-4 py-2 tabular-nums">{point.tokens_input.toLocaleString()}</td>
                <td className="px-4 py-2 tabular-nums">{point.tokens_output.toLocaleString()}</td>
                <td className="px-4 py-2 tabular-nums">{formatCompactCurrency(point.cost_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
