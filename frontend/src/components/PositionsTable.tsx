"use client";

import { Panel } from "./Panel";
import { flashClass, useFlash } from "@/hooks/useFlash";
import {
  formatMoney,
  formatPercent,
  formatPrice,
  formatQuantity,
  formatSignedMoney,
  toneClass,
} from "@/lib/format";
import type { PositionView, PriceMap } from "@/lib/types";

const HEADS = [
  "Symbol",
  "Qty",
  "Avg cost",
  "Last",
  "Value",
  "Unreal. P&L",
  "%",
];

function Row({
  position,
  price,
  selected,
  onSelect,
}: {
  position: PositionView;
  price: number;
  selected: boolean;
  onSelect: () => void;
}) {
  const flash = useFlash(price);
  const marketValue = position.quantity * price;
  const pnl = (price - position.avg_cost) * position.quantity;
  const pnlPercent = position.avg_cost
    ? (price / position.avg_cost - 1) * 100
    : 0;

  return (
    <tr
      data-testid={`position-row-${position.ticker}`}
      onClick={onSelect}
      className={`cursor-pointer border-b border-line-soft last:border-0 hover:bg-panel-head ${
        selected ? "bg-panel-head" : ""
      }`}
    >
      <td className="num px-2.5 py-1.5 font-semibold">{position.ticker}</td>
      <td className="num px-2.5 py-1.5 text-right">
        {formatQuantity(position.quantity)}
      </td>
      <td className="num px-2.5 py-1.5 text-right text-ink-muted">
        {formatPrice(position.avg_cost)}
      </td>
      <td className={`num px-2.5 py-1.5 text-right ${flashClass(flash)}`}>
        {formatPrice(price)}
      </td>
      <td className="num px-2.5 py-1.5 text-right">{formatMoney(marketValue)}</td>
      <td className={`num px-2.5 py-1.5 text-right ${toneClass(pnl)}`}>
        {formatSignedMoney(pnl)}
      </td>
      <td className={`num px-2.5 py-1.5 text-right ${toneClass(pnlPercent)}`}>
        {formatPercent(pnlPercent)}
      </td>
    </tr>
  );
}

interface PositionsTableProps {
  positions: PositionView[];
  prices: PriceMap;
  selected: string | null;
  onSelect: (ticker: string) => void;
  className?: string;
}

export function PositionsTable({
  positions,
  prices,
  selected,
  onSelect,
  className,
}: PositionsTableProps) {
  return (
    <Panel
      title="Positions"
      bodyClassName="overflow-auto scroll-thin"
      className={className}
    >
      {positions.length === 0 ? (
        <p className="px-2.5 py-4 text-xs text-ink-dim">
          No open positions. Use the trade bar or ask FinAlly to buy something.
        </p>
      ) : (
        <table
          data-testid="positions-table"
          className="w-full border-collapse text-xs"
        >
          <thead className="sticky top-0 bg-panel">
            <tr className="border-b border-line text-[9px] tracking-[0.12em] text-ink-dim uppercase">
              {HEADS.map((head, index) => (
                <th
                  key={head}
                  className={`px-2.5 py-1 font-medium ${
                    index === 0 ? "text-left" : "text-right"
                  }`}
                >
                  {head}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <Row
                key={position.ticker}
                position={position}
                price={prices[position.ticker]?.price ?? position.current_price}
                selected={position.ticker === selected}
                onSelect={() => onSelect(position.ticker)}
              />
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
