interface LegendEntry {
  id: string;
  label: string;
  color: string;
}

/** A legend is always present for 2+ series — the dependable identity
 * channel readers rely on instead of color-matching alone. A single-series
 * chart skips this; its title already names what's plotted. */
export function ChartLegend({ entries }: { entries: LegendEntry[] }) {
  if (entries.length < 2) return null;
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
      {entries.map((entry) => (
        <li key={entry.id} className="flex items-center gap-1.5">
          <span
            className="h-2.5 w-2.5 shrink-0 rounded-sm"
            style={{ backgroundColor: entry.color }}
            aria-hidden
          />
          {entry.label}
        </li>
      ))}
    </ul>
  );
}
