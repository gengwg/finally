"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";
import type { PriceMap } from "@/lib/types";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

export interface PricePoint {
  t: number;
  price: number;
}

/** Price series accumulated from the stream since page load, per ticker. */
export type PriceHistory = Record<string, PricePoint[]>;

/** ~200s of 500ms ticks — enough for the sparklines and the detail chart. */
const MAX_POINTS = 400;

const CLOSED = 2;

export interface PricesState {
  prices: PriceMap;
  history: PriceHistory;
  status: ConnectionStatus;
}

export function usePrices(): PricesState {
  const [prices, setPrices] = useState<PriceMap>({});
  const [history, setHistory] = useState<PriceHistory>({});
  const [status, setStatus] = useState<ConnectionStatus>("reconnecting");

  useEffect(() => {
    const source = new EventSource(`${API_BASE}/api/stream/prices`);

    source.onopen = () => setStatus("connected");
    // EventSource retries on its own; a closed socket is the only dead end.
    source.onerror = () =>
      setStatus(source.readyState === CLOSED ? "disconnected" : "reconnecting");

    source.onmessage = (event: MessageEvent<string>) => {
      let frame: PriceMap;
      try {
        frame = JSON.parse(event.data);
      } catch {
        return;
      }
      setStatus("connected");
      setPrices((prev) => ({ ...prev, ...frame }));
      setHistory((prev) => {
        const next = { ...prev };
        for (const [ticker, update] of Object.entries(frame)) {
          const series = next[ticker] ?? [];
          next[ticker] = [
            ...series.slice(Math.max(0, series.length - MAX_POINTS + 1)),
            { t: update.timestamp, price: update.price },
          ];
        }
        return next;
      });
    };

    return () => source.close();
  }, []);

  return { prices, history, status };
}
