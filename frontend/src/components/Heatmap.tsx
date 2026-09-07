"use client";

import { ResponsiveContainer, Treemap } from "recharts";
import { Panel } from "./Panel";
import { formatPercent } from "@/lib/format";
import type { PositionView } from "@/lib/types";

interface Cell {
  // Recharts' Treemap data type demands an index signature.
  [key: string]: string | number;
  name: string;
  size: number;
  pnl: number;
  pnlPercent: number;
}

export type PnlSign = "profit" | "loss" | "flat";

export const pnlSign = (pnl: number): PnlSign =>
  pnl > 0 ? "profit" : pnl < 0 ? "loss" : "flat";

/** Sign comes from the P&L, saturation from the move, capped at +/-5%. */
function tint(pnl: number, pnlPercent: number): string {
  const weight = Math.min(Math.abs(pnlPercent) / 5, 1) * 0.75 + 0.15;
  const base = pnl < 0 ? "var(--color-down)" : "var(--color-up)";
  return `color-mix(in srgb, ${base} ${(weight * 100).toFixed(0)}%, #131a24)`;
}

interface CellProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  depth?: number;
  name?: string;
  pnl?: number;
  pnlPercent?: number;
}

function CellShape({
  x = 0,
  y = 0,
  width = 0,
  height = 0,
  depth = 0,
  name,
  pnl = 0,
  pnlPercent = 0,
}: CellProps) {
  // Recharts renders content for every node including its synthetic root;
  // only the depth-1 leaves are actual positions.
  if (depth !== 1) return null;

  const roomy = width > 46 && height > 30;
  return (
    <g data-testid={`heatmap-tile-${name}`} data-pnl={pnlSign(pnl)}>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={tint(pnl, pnlPercent)}
        stroke="#131a24"
        strokeWidth={2}
      />
      {roomy && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 3}
            textAnchor="middle"
            fill="#e6edf3"
            fontSize={11}
            fontWeight={600}
            fontFamily="var(--font-mono)"
          >
            {name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 11}
            textAnchor="middle"
            fill="#e6edf3"
            fontSize={9}
            fontFamily="var(--font-mono)"
          >
            {formatPercent(pnlPercent)}
          </text>
        </>
      )}
    </g>
  );
}

export function Heatmap({
  positions,
  className,
}: {
  positions: PositionView[];
  className?: string;
}) {
  const data: Cell[] = positions
    .filter((position) => position.market_value > 0)
    .map((position) => ({
      name: position.ticker,
      size: position.market_value,
      pnl: position.unrealized_pnl,
      pnlPercent: position.pnl_percent,
    }));

  return (
    <Panel title="Portfolio heatmap" bodyClassName="p-1.5" className={className}>
      <div data-testid="heatmap" className="h-full w-full">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-ink-dim">
            No positions yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="size"
              isAnimationActive={false}
              content={<CellShape />}
            />
          </ResponsiveContainer>
        )}
      </div>
    </Panel>
  );
}
