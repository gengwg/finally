"use client";

import { useState } from "react";
import { formatMoney } from "@/lib/format";

interface TradeBarProps {
  ticker: string;
  onTickerChange: (ticker: string) => void;
  price: number | null;
  busy: boolean;
  error: string | null;
  onTrade: (ticker: string, quantity: number, side: "buy" | "sell") => void;
}

export function TradeBar({
  ticker,
  onTickerChange,
  price,
  busy,
  error,
  onTrade,
}: TradeBarProps) {
  const [quantity, setQuantity] = useState("1");

  const parsed = Number.parseFloat(quantity);
  const valid = ticker.trim().length > 0 && Number.isFinite(parsed) && parsed > 0;
  const notional = valid && price != null ? parsed * price : null;

  const submit = (side: "buy" | "sell") => {
    if (!valid) return;
    onTrade(ticker.trim().toUpperCase(), parsed, side);
  };

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2 rounded border border-line bg-panel px-2.5 py-2">
      <span className="text-[10px] tracking-[0.14em] text-ink-muted uppercase">
        Market order
      </span>
      <input
        data-testid="trade-ticker"
        aria-label="Trade ticker"
        value={ticker}
        onChange={(event) => onTickerChange(event.target.value.toUpperCase())}
        placeholder="TICKER"
        maxLength={5}
        className="num w-24 rounded border border-line bg-ground px-2 py-1 text-xs uppercase placeholder:text-ink-dim focus:border-brand focus:outline-none"
      />
      <input
        data-testid="trade-quantity"
        aria-label="Trade quantity"
        value={quantity}
        onChange={(event) => setQuantity(event.target.value)}
        inputMode="decimal"
        placeholder="QTY"
        className="num w-24 rounded border border-line bg-ground px-2 py-1 text-xs focus:border-brand focus:outline-none"
      />
      <button
        type="button"
        data-testid="trade-buy"
        disabled={!valid || busy}
        onClick={() => submit("buy")}
        className="rounded bg-up px-4 py-1 text-xs font-semibold text-ground hover:brightness-110 disabled:opacity-40"
      >
        Buy
      </button>
      <button
        type="button"
        data-testid="trade-sell"
        disabled={!valid || busy}
        onClick={() => submit("sell")}
        className="rounded bg-down px-4 py-1 text-xs font-semibold text-ground hover:brightness-110 disabled:opacity-40"
      >
        Sell
      </button>
      {notional != null && (
        <span className="num text-xs text-ink-muted">
          ≈ {formatMoney(notional)}
        </span>
      )}
      {error && (
        <span data-testid="trade-error" className="text-xs text-down">
          {error}
        </span>
      )}
    </div>
  );
}
