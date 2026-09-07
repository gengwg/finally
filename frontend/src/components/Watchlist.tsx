"use client";

import { useState } from "react";
import { Panel } from "./Panel";
import { Sparkline } from "./Sparkline";
import { flashClass, useFlash } from "@/hooks/useFlash";
import type { PriceHistory, PricePoint } from "@/hooks/usePrices";
import { formatPercent, formatPrice, toneClass } from "@/lib/format";
import type { PriceMap, WatchlistTicker } from "@/lib/types";

const ROW = "grid grid-cols-[1fr_5rem_4.75rem_4rem_1.25rem] items-center gap-2";

interface WatchlistProps {
  tickers: WatchlistTicker[];
  prices: PriceMap;
  history: PriceHistory;
  selected: string | null;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => void;
  onRemove: (ticker: string) => void;
  error?: string | null;
  className?: string;
}

function Row({
  entry,
  price,
  points,
  selected,
  onSelect,
  onRemove,
}: {
  entry: WatchlistTicker;
  price: number | null;
  points: PricePoint[];
  selected: boolean;
  onSelect: () => void;
  onRemove: () => void;
}) {
  const flash = useFlash(price);
  // Session change is measured against the first price seen since page load.
  const first = points[0]?.price;
  const changePercent =
    price != null && first ? (price / first - 1) * 100 : entry.change_percent;

  return (
    <div
      data-testid={`watchlist-row-${entry.ticker}`}
      data-selected={selected}
      onClick={onSelect}
      className={`${ROW} group cursor-pointer border-l-2 px-2.5 py-1.5 hover:bg-panel-head ${
        selected ? "border-brand bg-panel-head" : "border-transparent"
      }`}
    >
      <span className="num text-xs font-semibold">{entry.ticker}</span>
      <span
        data-testid={`watchlist-price-${entry.ticker}`}
        className={`num rounded px-1 text-right text-xs ${flashClass(flash)}`}
      >
        {formatPrice(price)}
      </span>
      <span className={`num text-right text-xs ${toneClass(changePercent)}`}>
        {formatPercent(changePercent)}
      </span>
      <Sparkline points={points} rising={(changePercent ?? 0) >= 0} />
      <button
        type="button"
        aria-label={`Remove ${entry.ticker}`}
        data-testid={`watchlist-remove-${entry.ticker}`}
        onClick={(event) => {
          event.stopPropagation();
          onRemove();
        }}
        className="text-ink-dim opacity-0 transition group-hover:opacity-100 hover:text-down focus:opacity-100"
      >
        ×
      </button>
    </div>
  );
}

export function Watchlist({
  tickers,
  prices,
  history,
  selected,
  onSelect,
  onAdd,
  onRemove,
  error,
  className,
}: WatchlistProps) {
  const [draft, setDraft] = useState("");

  const submit = () => {
    const ticker = draft.trim().toUpperCase();
    if (!ticker) return;
    onAdd(ticker);
    setDraft("");
  };

  return (
    <Panel
      title="Watchlist"
      className={className}
      bodyClassName="flex flex-col min-h-0"
    >
      <div
        className={`${ROW} shrink-0 border-b border-line-soft px-2.5 py-1 text-[9px] tracking-[0.12em] text-ink-dim uppercase`}
      >
        <span>Symbol</span>
        <span className="text-right">Last</span>
        <span className="text-right">Chg</span>
        <span />
        <span />
      </div>

      <div
        data-testid="watchlist"
        className="scroll-thin min-h-0 flex-1 overflow-y-auto"
      >
        {tickers.map((entry) => (
          <Row
            key={entry.ticker}
            entry={entry}
            price={prices[entry.ticker]?.price ?? entry.price}
            points={history[entry.ticker] ?? []}
            selected={entry.ticker === selected}
            onSelect={() => onSelect(entry.ticker)}
            onRemove={() => onRemove(entry.ticker)}
          />
        ))}
      </div>

      <form
        className="shrink-0 border-t border-line bg-panel-head px-2 py-2"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <div className="flex gap-1.5">
          <input
            data-testid="watchlist-add-input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Add ticker"
            maxLength={5}
            aria-label="Add ticker"
            className="num min-w-0 flex-1 rounded border border-line bg-ground px-2 py-1 text-xs uppercase placeholder:normal-case placeholder:text-ink-dim focus:border-brand focus:outline-none"
          />
          <button
            type="submit"
            data-testid="watchlist-add-submit"
            className="rounded bg-brand px-2.5 py-1 text-xs font-semibold text-ground hover:brightness-110"
          >
            Add
          </button>
        </div>
        {error && (
          <p className="mt-1.5 text-[10px] text-down">{error}</p>
        )}
      </form>
    </Panel>
  );
}
