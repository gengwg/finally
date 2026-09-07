"use client";

import { useCallback, useEffect, useState } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { Header } from "@/components/Header";
import { Heatmap } from "@/components/Heatmap";
import { MainChart } from "@/components/MainChart";
import { PnlChart } from "@/components/PnlChart";
import { PositionsTable } from "@/components/PositionsTable";
import { TradeBar } from "@/components/TradeBar";
import { Watchlist } from "@/components/Watchlist";
import { usePrices } from "@/hooks/usePrices";
import * as api from "@/lib/api";
import type {
  ChatMessage,
  Portfolio,
  Snapshot,
  WatchlistTicker,
} from "@/lib/types";

const SNAPSHOT_POLL_MS = 30_000;

const message = (error: unknown) =>
  error instanceof Error ? error.message : "Request failed";

export default function Workstation() {
  const { prices, history, status } = usePrices();

  const [watchlist, setWatchlist] = useState<WatchlistTicker[]>([]);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [chat, setChat] = useState<ChatMessage[]>([]);

  const [selected, setSelected] = useState<string | null>(null);
  const [tradeTicker, setTradeTicker] = useState("");

  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [tradeError, setTradeError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [tradeBusy, setTradeBusy] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);

  useEffect(() => {
    api
      .getWatchlist()
      .then((list) => {
        setWatchlist(list);
        setTradeTicker((current) => current || (list[0]?.ticker ?? ""));
      })
      .catch(() => {});
    api.getPortfolio().then(setPortfolio).catch(() => {});
    api.getPortfolioHistory().then(setSnapshots).catch(() => {});
    api.getChatHistory().then(setChat).catch(() => {});
  }, []);

  // The backend snapshots portfolio value every 30s; stay roughly in step.
  useEffect(() => {
    const timer = setInterval(() => {
      api.getPortfolioHistory().then(setSnapshots).catch(() => {});
      api.getPortfolio().then(setPortfolio).catch(() => {});
    }, SNAPSHOT_POLL_MS);
    return () => clearInterval(timer);
  }, []);

  const select = useCallback((ticker: string) => {
    setSelected(ticker);
    setTradeTicker(ticker);
    setTradeError(null);
  }, []);

  // The first watchlist entry stands in until the user picks a ticker.
  const activeTicker = selected ?? watchlist[0]?.ticker ?? null;

  const livePrice = (ticker: string, fallback: number) =>
    prices[ticker]?.price ?? fallback;

  const positions = portfolio?.positions ?? [];

  const totalValue = positions.reduce(
    (total, position) =>
      total +
      position.quantity * livePrice(position.ticker, position.current_price),
    portfolio?.cash_balance ?? 0,
  );

  const unrealizedPnl = positions.reduce(
    (total, position) =>
      total +
      (livePrice(position.ticker, position.current_price) - position.avg_cost) *
        position.quantity,
    0,
  );

  const addTicker = async (ticker: string) => {
    setWatchlistError(null);
    try {
      setWatchlist(await api.addWatchlistTicker(ticker));
    } catch (error) {
      setWatchlistError(message(error));
    }
  };

  const removeTicker = async (ticker: string) => {
    setWatchlistError(null);
    try {
      const next = await api.removeWatchlistTicker(ticker);
      setWatchlist(next);
      if (ticker === activeTicker) setSelected(null);
    } catch (error) {
      setWatchlistError(message(error));
    }
  };

  const trade = async (
    ticker: string,
    quantity: number,
    side: "buy" | "sell",
  ) => {
    setTradeError(null);
    setTradeBusy(true);
    try {
      const result = await api.executeTrade(ticker, quantity, side);
      setPortfolio(result.portfolio);
      api.getWatchlist().then(setWatchlist).catch(() => {});
      api.getPortfolioHistory().then(setSnapshots).catch(() => {});
    } catch (error) {
      setTradeError(message(error));
    } finally {
      setTradeBusy(false);
    }
  };

  const sendChat = async (text: string) => {
    setChatError(null);
    setChatBusy(true);
    const now = new Date().toISOString();
    setChat((prev) => [
      ...prev,
      { role: "user", content: text, actions: null, created_at: now },
    ]);
    try {
      const reply = await api.sendChatMessage(text);
      setChat((prev) => [
        ...prev,
        {
          role: "assistant",
          content: reply.message,
          actions: {
            trades: reply.trades ?? [],
            watchlist_changes: reply.watchlist_changes ?? [],
          },
          created_at: new Date().toISOString(),
        },
      ]);
      setPortfolio(reply.portfolio);
      api.getWatchlist().then(setWatchlist).catch(() => {});
      api.getPortfolioHistory().then(setSnapshots).catch(() => {});
    } catch (error) {
      setChatError(message(error));
    } finally {
      setChatBusy(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <Header
        totalValue={totalValue}
        cashBalance={portfolio?.cash_balance ?? 0}
        unrealizedPnl={unrealizedPnl}
        status={status}
      />

      <main className="flex min-h-0 flex-1 gap-2 p-2">
        <Watchlist
          className="w-[20rem] shrink-0"
          tickers={watchlist}
          prices={prices}
          history={history}
          selected={activeTicker}
          onSelect={select}
          onAdd={addTicker}
          onRemove={removeTicker}
          error={watchlistError}
        />

        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <MainChart
            className="min-h-[10rem] flex-[3]"
            ticker={activeTicker}
            points={activeTicker ? (history[activeTicker] ?? []) : []}
          />
          <div className="flex min-h-0 flex-[2] gap-2">
            <Heatmap className="min-w-0 flex-1" positions={positions} />
            <PnlChart className="min-w-0 flex-1" snapshots={snapshots} />
          </div>
          <PositionsTable
            className="min-h-[6rem] flex-[2]"
            positions={positions}
            prices={prices}
            selected={activeTicker}
            onSelect={select}
          />
          <TradeBar
            ticker={tradeTicker}
            onTickerChange={setTradeTicker}
            price={
              tradeTicker
                ? (prices[tradeTicker.toUpperCase()]?.price ?? null)
                : null
            }
            busy={tradeBusy}
            error={tradeError}
            onTrade={trade}
          />
        </div>

        <ChatPanel
          messages={chat}
          busy={chatBusy}
          error={chatError}
          onSend={sendChat}
        />
      </main>
    </div>
  );
}
