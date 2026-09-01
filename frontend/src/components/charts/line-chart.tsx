"use client";

import { useId, useMemo, useState } from "react";

import { ChartLegend } from "@/components/charts/chart-legend";
import { formatShortDate } from "@/components/charts/format";

export interface LineChartSeries {
  id: string;
  label: string;
  color: string;
  values: number[];
}

interface LineChartProps {
  days: string[];
  series: LineChartSeries[];
  valueFormatter?: (value: number) => string;
  height?: number;
}

const WIDTH = 720;
const PADDING = { top: 16, right: 16, bottom: 26, left: 44 };

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

/** Multi-series time-series line chart (SVG, no charting library). Single
 * series gets an area wash (per dataviz "trend over time" guidance); 2+
 * series stay as bare lines with a mandatory legend since color alone
 * shouldn't carry identity past one series. */
export function LineChart({ days, series, valueFormatter, height = 220 }: LineChartProps) {
  const gradientId = useId();
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const plotW = WIDTH - PADDING.left - PADDING.right;
  const plotH = height - PADDING.top - PADDING.bottom;
  const formatValue = valueFormatter ?? ((v: number) => v.toLocaleString());

  const maxValue = useMemo(() => {
    const rawMax = Math.max(0, ...series.flatMap((s) => s.values));
    return niceMax(rawMax);
  }, [series]);

  const xAt = (i: number) => PADDING.left + (days.length <= 1 ? 0 : (i / (days.length - 1)) * plotW);
  const yAt = (v: number) => PADDING.top + plotH - (v / maxValue) * plotH;

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => maxValue * f);
  const xTickStride = Math.max(1, Math.ceil(days.length / 6));

  function handlePointerMove(event: React.PointerEvent<SVGRectElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const relativeX = (event.clientX - rect.left) / rect.width;
    const idx = Math.round(relativeX * (days.length - 1));
    setActiveIndex(clamp(idx, 0, days.length - 1));
  }

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

  const showArea = series.length === 1;
  const activeDay = activeIndex !== null ? days[activeIndex] : null;

  const tooltipLines = activeIndex !== null ? series.map((s) => ({ ...s, value: s.values[activeIndex] ?? 0 })) : [];
  const tooltipBoxHeight = 20 + tooltipLines.length * 16 + 8;
  const tooltipBoxWidth = 200;
  const rawTooltipX = activeIndex !== null ? xAt(activeIndex) + 10 : 0;
  const tooltipX =
    rawTooltipX + tooltipBoxWidth > WIDTH - PADDING.right
      ? (activeIndex !== null ? xAt(activeIndex) : 0) - tooltipBoxWidth - 10
      : rawTooltipX;
  const tooltipY = PADDING.top + 4;

  return (
    <div
      className="w-full focus:outline-none"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onFocus={() => setActiveIndex((prev) => prev ?? days.length - 1)}
      onBlur={() => setActiveIndex(null)}
      role="img"
      aria-label={`Line chart of ${series.map((s) => s.label).join(", ")} over ${days.length} days`}
    >
      <svg viewBox={`0 0 ${WIDTH} ${height}`} className="w-full" style={{ overflow: "visible" }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={series[0]?.color} stopOpacity={0.16} />
            <stop offset="100%" stopColor={series[0]?.color} stopOpacity={0} />
          </linearGradient>
        </defs>

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
              x={xAt(i)}
              y={height - 6}
              textAnchor="middle"
              className="fill-muted-foreground"
              fontSize={10}
            >
              {formatShortDate(day)}
            </text>
          ) : null,
        )}

        {showArea && series[0] && (
          <path
            d={`${series[0].values.map((v, i) => `${i === 0 ? "M" : "L"}${xAt(i)},${yAt(v)}`).join(" ")} L${xAt(
              series[0].values.length - 1,
            )},${yAt(0)} L${xAt(0)},${yAt(0)} Z`}
            fill={`url(#${gradientId})`}
            stroke="none"
          />
        )}

        {series.map((s) => (
          <path
            key={s.id}
            d={s.values.map((v, i) => `${i === 0 ? "M" : "L"}${xAt(i)},${yAt(v)}`).join(" ")}
            fill="none"
            stroke={s.color}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {series.map((s) => {
          const lastIdx = s.values.length - 1;
          return (
            <circle
              key={s.id}
              cx={xAt(lastIdx)}
              cy={yAt(s.values[lastIdx] ?? 0)}
              r={4}
              fill={s.color}
              stroke="hsl(var(--card))"
              strokeWidth={2}
            />
          );
        })}

        {/* Hover/focus overlay: transparent hit area spanning the full plot,
            bigger than the marks themselves, per interaction.md. */}
        <rect
          x={PADDING.left}
          y={0}
          width={plotW}
          height={height}
          fill="transparent"
          onPointerMove={handlePointerMove}
          onPointerLeave={() => setActiveIndex(null)}
        />

        {activeIndex !== null && activeDay && (
          <g>
            <line
              x1={xAt(activeIndex)}
              x2={xAt(activeIndex)}
              y1={PADDING.top}
              y2={height - PADDING.bottom}
              stroke="hsl(var(--chart-axis))"
              strokeWidth={1}
            />
            {series.map((s) => (
              <circle
                key={s.id}
                cx={xAt(activeIndex)}
                cy={yAt(s.values[activeIndex] ?? 0)}
                r={4}
                fill={s.color}
                stroke="hsl(var(--card))"
                strokeWidth={2}
              />
            ))}

            <g transform={`translate(${tooltipX}, ${tooltipY})`}>
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
              {tooltipLines.map((line, i) => (
                <g key={line.id} transform={`translate(10, ${32 + i * 16})`}>
                  <line x1={0} y1={-4} x2={10} y2={-4} stroke={line.color} strokeWidth={2} />
                  <text x={16} y={0} fontSize={11} fontWeight={600} className="fill-foreground">
                    {formatValue(line.value)}
                  </text>
                  <text x={tooltipBoxWidth - 20} y={0} textAnchor="end" fontSize={10} className="fill-muted-foreground">
                    {line.label}
                  </text>
                </g>
              ))}
            </g>
          </g>
        )}
      </svg>

      <ChartLegend entries={series.map((s) => ({ id: s.id, label: s.label, color: s.color }))} />
    </div>
  );
}
