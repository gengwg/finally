import type {
  ChatMessage,
  Portfolio,
  PriceMap,
  WatchlistTicker,
} from "@/lib/types";

export const priceMap = (prices: Record<string, number>): PriceMap =>
  Object.fromEntries(
    Object.entries(prices).map(([ticker, price]) => [
      ticker,
      {
        ticker,
        price,
        previous_price: price,
        timestamp: 1757246400,
        change: 0,
        change_percent: 0,
        direction: "flat" as const,
      },
    ]),
  );

export const watchlistEntry = (
  ticker: string,
  price: number | null = null,
): WatchlistTicker => ({
  ticker,
  added_at: "2026-09-07T12:00:00+00:00",
  price,
  previous_price: price,
  change: 0,
  change_percent: 0,
  direction: "flat",
});

export const portfolio: Portfolio = {
  cash_balance: 8080.0,
  positions: [
    {
      ticker: "AAPL",
      quantity: 10,
      avg_cost: 192.0,
      current_price: 193.5,
      market_value: 1935.0,
      unrealized_pnl: 15.0,
      pnl_percent: 0.78,
    },
    {
      ticker: "TSLA",
      quantity: 4,
      avg_cost: 250.0,
      current_price: 240.0,
      market_value: 960.0,
      unrealized_pnl: -40.0,
      pnl_percent: -4.0,
    },
  ],
  positions_value: 2895.0,
  total_value: 10975.0,
  total_unrealized_pnl: -25.0,
};

export const chatHistory: ChatMessage[] = [
  {
    role: "user",
    content: "buy me 10 apple shares",
    actions: null,
    created_at: "2026-09-07T12:00:00+00:00",
  },
  {
    role: "assistant",
    content: "Bought 10 AAPL at $192.00.",
    actions: {
      trades: [
        {
          ticker: "AAPL",
          side: "buy",
          quantity: 10,
          status: "executed",
          price: 192.0,
          error: null,
        },
      ],
      watchlist_changes: [
        { ticker: "PYPL", action: "add", status: "executed", error: null },
      ],
    },
    created_at: "2026-09-07T12:00:01+00:00",
  },
];
