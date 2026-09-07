"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Panel } from "./Panel";
import type { PricePoint } from "@/hooks/usePrices";
import { formatPercent, formatPrice, toneClass } from "@/lib/format";

const AXIS = { stroke: "#5f6b78", fontSize: 10, fontFamily: "var(--font-mono)" };

const clock = (t: number) =>
  new Date(t * 1000).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

interface MainChartProps {
  ticker: string | null;
  points: PricePoint[];
  className?: string;
}

export function MainChart({ ticker, points, className }: MainChartProps) {
  const first = points[0]?.price;
  const last = points[points.length - 1]?.price;
  const changePercent = first && last ? (last / first - 1) * 100 : null;
  const rising = (changePercent ?? 0) >= 0;
  const colour = rising ? "var(--color-up)" : "var(--color-down)";

  return (
    <Panel
      title={ticker ? `${ticker} — session` : "Session chart"}
      bodyClassName="p-2"
      className={className}
      actions={
        <div className="flex items-baseline gap-2">
          <span className="num text-sm font-semibold">{formatPrice(last)}</span>
          <span className={`num text-xs ${toneClass(changePercent)}`}>
            {formatPercent(changePercent)}
          </span>
        </div>
      }
    >
      <div
        data-testid="main-chart"
        data-ticker={ticker ?? ""}
        className="h-full w-full"
      >
        {points.length < 2 ? (
          <div className="flex h-full items-center justify-center text-xs text-ink-dim">
            Waiting for price data…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colour} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={colour} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1b2330" vertical={false} />
              <XAxis
                dataKey="t"
                tickFormatter={clock}
                tick={AXIS}
                minTickGap={48}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                orientation="right"
                domain={["dataMin", "dataMax"]}
                tickFormatter={formatPrice}
                tick={AXIS}
                width={56}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                labelFormatter={(label) => clock(Number(label))}
                formatter={(value) => [formatPrice(Number(value)), "Price"]}
                contentStyle={{
                  background: "#182029",
                  border: "1px solid #232c38",
                  borderRadius: 4,
                  fontSize: 11,
                }}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke={colour}
                strokeWidth={1.5}
                fill="url(#chart-fill)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Panel>
  );
}
