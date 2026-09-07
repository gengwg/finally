import type {
  ChatMessage,
  ChatReply,
  Portfolio,
  Snapshot,
  Trade,
  WatchlistTicker,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

/** Errors from the API carry a `detail` string, which is what the user sees. */
export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
  });
  if (!res.ok) {
    const detail = await res
      .json()
      .then((body) => body?.detail)
      .catch(() => null);
    throw new ApiError(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const getPortfolio = () => request<Portfolio>("/api/portfolio");

export const getPortfolioHistory = () =>
  request<{ snapshots: Snapshot[] }>("/api/portfolio/history").then(
    (r) => r.snapshots,
  );

export const getWatchlist = () =>
  request<{ tickers: WatchlistTicker[] }>("/api/watchlist").then(
    (r) => r.tickers,
  );

export const addWatchlistTicker = (ticker: string) =>
  request<{ tickers: WatchlistTicker[] }>("/api/watchlist", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  }).then((r) => r.tickers);

export const removeWatchlistTicker = (ticker: string) =>
  request<{ tickers: WatchlistTicker[] }>(`/api/watchlist/${ticker}`, {
    method: "DELETE",
  }).then((r) => r.tickers);

export const executeTrade = (
  ticker: string,
  quantity: number,
  side: "buy" | "sell",
) =>
  request<{ trade: Trade; portfolio: Portfolio }>("/api/portfolio/trade", {
    method: "POST",
    body: JSON.stringify({ ticker, quantity, side }),
  });

export const getChatHistory = () =>
  request<{ messages: ChatMessage[] }>("/api/chat/history").then(
    (r) => r.messages,
  );

export const sendChatMessage = (message: string) =>
  request<ChatReply>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
