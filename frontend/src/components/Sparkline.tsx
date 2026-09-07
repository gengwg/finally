"use client";

import { Line, LineChart, YAxis } from "recharts";
import type { PricePoint } from "@/hooks/usePrices";

interface SparklineProps {
  points: PricePoint[];
  rising: boolean;
  width?: number;
  height?: number;
}

export function Sparkline({
  points,
  rising,
  width = 64,
  height = 22,
}: SparklineProps) {
  if (points.length < 2) {
    return (
      <div
        style={{ width, height }}
        className="flex items-center justify-center text-[9px] text-ink-dim"
      >
        ···
      </div>
    );
  }

  return (
    <LineChart
      width={width}
      height={height}
      data={points}
      margin={{ top: 2, right: 0, bottom: 2, left: 0 }}
    >
      <YAxis hide domain={["dataMin", "dataMax"]} />
      <Line
        type="monotone"
        dataKey="price"
        stroke={rising ? "var(--color-up)" : "var(--color-down)"}
        strokeWidth={1.25}
        dot={false}
        isAnimationActive={false}
      />
    </LineChart>
  );
}
