"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Panel } from "./Panel";
import { formatClock, formatMoney, moneyAxisFormatter } from "@/lib/format";
import type { Snapshot } from "@/lib/types";

const AXIS = { stroke: "#5f6b78", fontSize: 10, fontFamily: "var(--font-mono)" };

export function PnlChart({
  snapshots,
  className,
}: {
  snapshots: Snapshot[];
  className?: string;
}) {
  const data = snapshots.map((snapshot) => ({
    label: formatClock(snapshot.recorded_at),
    value: snapshot.total_value,
  }));

  const values = data.map((point) => point.value);
  const span = values.length ? Math.max(...values) - Math.min(...values) : 0;
  const formatTick = moneyAxisFormatter(span);

  return (
    <Panel title="Portfolio value" bodyClassName="p-2" className={className}>
      <div data-testid="pnl-chart" className="h-full w-full">
        {data.length < 2 ? (
          <div className="flex h-full items-center justify-center text-xs text-ink-dim">
            Collecting snapshots…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#1b2330" vertical={false} />
              <XAxis
                dataKey="label"
                tick={AXIS}
                minTickGap={40}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                orientation="right"
                domain={["dataMin", "dataMax"]}
                tickFormatter={formatTick}
                tick={AXIS}
                width={span >= 10_000 ? 56 : 76}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                formatter={(value) => [formatMoney(Number(value)), "Value"]}
                contentStyle={{
                  background: "#182029",
                  border: "1px solid #232c38",
                  borderRadius: 4,
                  fontSize: 11,
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--color-accent)"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Panel>
  );
}
