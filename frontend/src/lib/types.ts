export type Direction = "up" | "down" | "flat";

/** One frame of `/api/stream/prices` carries a map of these, keyed by ticker. */
export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number | null;
  timestamp: number;
  change: number | null;
  change_percent: number | null;
  direction: Direction;
}

export type PriceMap = Record<string, PriceUpdate>;

export interface WatchlistTicker {
  ticker: string;
  added_at: string;
  price: number | null;
  previous_price: number | null;
  change: number | null;
  change_percent: number | null;
  direction: Direction | null;
}

export interface PositionView {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  pnl_percent: number;
}

export interface Portfolio {
  cash_balance: number;
  positions: PositionView[];
  positions_value: number;
  total_value: number;
  total_unrealized_pnl: number;
}

export interface Snapshot {
  total_value: number;
  recorded_at: string;
}

export interface Trade {
  id: string;
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  executed_at: string;
}

export interface TradeAction {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  status: "executed" | "failed";
  price: number | null;
  error: string | null;
}

export interface WatchlistAction {
  ticker: string;
  action: "add" | "remove";
  status: "executed" | "failed";
  error: string | null;
}

export interface ChatActions {
  trades?: TradeAction[];
  watchlist_changes?: WatchlistAction[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  actions: ChatActions | null;
  created_at: string;
}

export interface ChatReply extends ChatActions {
  message: string;
  portfolio: Portfolio;
}
