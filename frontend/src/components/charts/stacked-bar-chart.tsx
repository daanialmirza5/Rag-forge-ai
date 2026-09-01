"use client";

import { useMemo, useState } from "react";

import { ChartLegend } from "@/components/charts/chart-legend";
import { formatShortDate } from "@/components/charts/format";

export interface StackedBarSeries {
  id: string;
  label: string;
  color: string;
  values: number[];
}

interface StackedBarChartProps {
  days: string[];
  series: StackedBarSeries[];
  valueFormatter?: (value: number) => string;
  height?: number;
}

const WIDTH = 720;
const PADDING = { top: 16, right: 16, bottom: 26, left: 44 };
const MAX_BAR_WIDTH = 24;
const SEGMENT_GAP = 2;

function niceMax(rawMax: number): number {
  if (rawMax <= 0) return 1;
  const exponent = Math.floor(Math.log10(rawMax));
  const fraction = rawMax / 10 ** exponent;
  const niceFraction = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10;
  return niceFraction * 10 ** exponent;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/** Per-day stacked bar chart for a fixed, ordered set of event-type series.
 * Segments get a 2px surface-color gap instead of a border (dataviz
 * marks-and-anatomy); the whole day-column is the hover/focus hit target
 * since individual segments are too thin to reliably land on. */
export function StackedBarChart({ days, series, valueFormatter, height = 220 }: StackedBarChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const plotW = WIDTH - PADDING.left - PADDING.right;
  const plotH = height - PADDING.top - PADDING.bottom;
  const formatValue = valueFormatter ?? ((v: number) => v.toLocaleString());

  const totals = useMemo(
    () => days.map((_, i) => series.reduce((sum, s) => sum + (s.values[i] ?? 0), 0)),
    [days, series],
  );
  const maxValue = useMemo(() => niceMax(Math.max(0, ...totals)), [totals]);

  const bandWidth = plotW / days.length;
  const barWidth = Math.min(MAX_BAR_WIDTH, bandWidth * 0.6);

  const yAt = (v: number) => PADDING.top + plotH - (v / maxValue) * plotH;
  const barX = (i: number) => PADDING.left + i * bandWidth + (bandWidth - barWidth) / 2;

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => maxValue * f);
  const xTickStride = Math.max(1, Math.ceil(days.length / 6));

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      setActiveIndex((prev) => clamp((prev ?? -1) + 1, 0, days.length - 1));
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      setActiveIndex((prev) => clamp((prev ?? days.length) - 1, 0, days.length - 1));
    } else if (event.key === "Escape") {
      setActiveIndex(null);
    }
  }

  const activeDay = activeIndex !== null ? days[activeIndex] : null;
  const tooltipLines =
    activeIndex !== null
      ? series
          .map((s) => ({ ...s, value: s.values[activeIndex] ?? 0 }))
          .filter((s) => s.value > 0)
      : [];
  const tooltipBoxHeight = 20 + Math.max(tooltipLines.length, 1) * 16 + 8;
  const tooltipBoxWidth = 200;
  const rawTooltipX = activeIndex !== null ? barX(activeIndex) + barWidth + 10 : 0;
  const tooltipX =
    rawTooltipX + tooltipBoxWidth > WIDTH - PADDING.right
      ? (activeIndex !== null ? barX(activeIndex) : 0) - tooltipBoxWidth - 10
      : rawTooltipX;

  return (
    <div
      className="w-full focus:outline-none"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onFocus={() => setActiveIndex((prev) => prev ?? days.length - 1)}
      onBlur={() => setActiveIndex(null)}
      role="img"
      aria-label={`Stacked bar chart of ${series.map((s) => s.label).join(", ")} over ${days.length} days`}
    >
      <svg viewBox={`0 0 ${WIDTH} ${height}`} className="w-full" style={{ overflow: "visible" }}>
        {yTicks.map((tick) => (
          <g key={tick}>
            <line
              x1={PADDING.left}
              x2={WIDTH - PADDING.right}
              y1={yAt(tick)}
              y2={yAt(tick)}
              stroke="hsl(var(--chart-grid))"
              strokeWidth={1}
            />
            <text
              x={PADDING.left - 8}
              y={yAt(tick)}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-muted-foreground"
              fontSize={10}
            >
              {formatValue(tick)}
            </text>
          </g>
        ))}

        {days.map((day, i) =>
          i % xTickStride === 0 || i === days.length - 1 ? (
            <text
              key={day}
              x={barX(i) + barWidth / 2}
              y={height - 6}
              textAnchor="middle"
              className="fill-muted-foreground"
              fontSize={10}
            >
              {formatShortDate(day)}
            </text>
          ) : null,
        )}

        {days.map((_, dayIndex) => {
          const visibleSegments = series
            .map((s) => ({ ...s, value: s.values[dayIndex] ?? 0 }))
            .filter((s) => s.value > 0);
          let cumulative = 0;
          return (
            <g key={days[dayIndex]}>
              {visibleSegments.map((segment, segIndex) => {
                const segTop = cumulative + segment.value;
                const isBottom = segIndex === 0;
                const isTop = segIndex === visibleSegments.length - 1;
                cumulative = segTop;

                const rawY = yAt(segTop);
                const rawHeight = yAt(cumulative - segment.value) - rawY;
                const insetTop = isTop ? 0 : SEGMENT_GAP / 2;
                const insetBottom = isBottom ? 0 : SEGMENT_GAP / 2;
                const y = rawY + insetTop;
                const segHeight = Math.max(0, rawHeight - insetTop - insetBottom);
                const radius = isTop ? 4 : 0;

                return (
                  <path
                    key={segment.id}
                    d={roundedTopRectPath(barX(dayIndex), y, barWidth, segHeight, radius)}
                    fill={segment.color}
                    opacity={activeIndex === null || activeIndex === dayIndex ? 1 : 0.45}
                  />
                );
              })}
              <rect
                x={PADDING.left + dayIndex * bandWidth}
                y={PADDING.top}
                width={bandWidth}
                height={plotH}
                fill="transparent"
                onPointerEnter={() => setActiveIndex(dayIndex)}
                onPointerLeave={() => setActiveIndex(null)}
              />
            </g>
          );
        })}

        {activeIndex !== null && activeDay && (
          <g transform={`translate(${tooltipX}, ${PADDING.top + 4})`}>
            <rect
              width={tooltipBoxWidth}
              height={tooltipBoxHeight}
              rx={6}
              className="fill-popover stroke-border"
              strokeWidth={1}
            />
            <text x={10} y={16} fontSize={10} className="fill-muted-foreground">
              {formatShortDate(activeDay)}
            </text>
            {tooltipLines.length === 0 ? (
              <text x={10} y={32} fontSize={11} className="fill-muted-foreground">
                No usage
              </text>
            ) : (
              tooltipLines.map((line, i) => (
                <g key={line.id} transform={`translate(10, ${32 + i * 16})`}>
                  <line x1={0} y1={-4} x2={10} y2={-4} stroke={line.color} strokeWidth={2} />
                  <text x={16} y={0} fontSize={11} fontWeight={600} className="fill-foreground">
                    {formatValue(line.value)}
                  </text>
                  <text x={tooltipBoxWidth - 20} y={0} textAnchor="end" fontSize={10} className="fill-muted-foreground">
                    {line.label}
                  </text>
                </g>
              ))
            )}
          </g>
        )}
      </svg>

      <ChartLegend entries={series.map((s) => ({ id: s.id, label: s.label, color: s.color }))} />
    </div>
  );
}

function roundedTopRectPath(x: number, y: number, width: number, height: number, radius: number): string {
  if (height <= 0) return "";
  const r = Math.min(radius, height, width / 2);
  if (r <= 0) {
    return `M${x},${y} h${width} v${height} h${-width} Z`;
  }
  return [
    `M${x},${y + r}`,
    `a${r},${r} 0 0 1 ${r},${-r}`,
    `h${width - 2 * r}`,
    `a${r},${r} 0 0 1 ${r},${r}`,
    `v${height - r}`,
    `h${-width}`,
    `Z`,
  ].join(" ");
}
