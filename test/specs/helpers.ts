import { expect, request, type APIRequestContext, type Locator, type Page } from '@playwright/test';

export const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:8000';

export const DEFAULT_TICKERS = [
  'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'NFLX',
];

export type PositionView = {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  pnl_percent: number;
};

export type PortfolioView = {
  cash_balance: number;
  positions: PositionView[];
  positions_value: number;
  total_value: number;
  total_unrealized_pnl: number;
};

export type WatchlistEntry = {
  ticker: string;
  added_at: string;
  price: number | null;
  previous_price: number | null;
  change: number | null;
  change_percent: number | null;
  direction: string | null;
};

export type ChatAction = { status: string; error: string | null };
export type ChatTrade = ChatAction & { ticker: string; side: string; quantity: number; price: number | null };
export type ChatWatchlistChange = ChatAction & { ticker: string; action: string };
export type ChatActions = { trades?: ChatTrade[]; watchlist_changes?: ChatWatchlistChange[] } | null;
export type ChatHistoryMessage = { role: string; content: string; actions: ChatActions; created_at: string };

async function json<T>(request: APIRequestContext, path: string): Promise<T> {
  const response = await request.get(path);
  expect(response.ok(), `GET ${path} returned ${response.status()}`).toBeTruthy();
  return response.json() as Promise<T>;
}

export function getPortfolio(request: APIRequestContext): Promise<PortfolioView> {
  return json<PortfolioView>(request, '/api/portfolio');
}

export async function getWatchlist(request: APIRequestContext): Promise<WatchlistEntry[]> {
  const body = await json<{ tickers: WatchlistEntry[] }>(request, '/api/watchlist');
  return body.tickers;
}

export async function getSnapshots(request: APIRequestContext): Promise<{ total_value: number; recorded_at: string }[]> {
  const body = await json<{ snapshots: { total_value: number; recorded_at: string }[] }>(request, '/api/portfolio/history');
  return body.snapshots;
}

export async function getChatHistory(request: APIRequestContext): Promise<ChatHistoryMessage[]> {
  const body = await json<{ messages: ChatHistoryMessage[] }>(request, '/api/chat/history');
  return body.messages;
}

export function position(portfolio: PortfolioView, ticker: string): PositionView {
  const found = portfolio.positions.find((p) => p.ticker === ticker);
  expect(found, `no ${ticker} position in ${JSON.stringify(portfolio.positions)}`).toBeDefined();
  return found as PositionView;
}

/** "$8,080.00", "-$12.34" and "(12.34)" all parse to a plain number; "-" gives NaN. */
export function toMoney(text: string): number {
  const trimmed = text.trim();
  const negative = trimmed.startsWith('-') || /^\(.*\)$/.test(trimmed);
  const value = Number.parseFloat(trimmed.replace(/[^\d.]/g, ''));
  return Number.isFinite(value) ? (negative ? -value : value) : Number.NaN;
}

/** Asserting parse, for one-shot reads. Never call this inside an expect.poll body: a
 *  throw there aborts the poll instead of retrying. Use pollMoney for that. */
export function parseMoney(text: string): number {
  const value = toMoney(text);
  expect(Number.isFinite(value), `expected a number, got "${text}"`).toBeTruthy();
  return value;
}

export async function readMoney(locator: Locator): Promise<number> {
  return parseMoney(await locator.innerText());
}

/** Poll-safe: NaN while the element is missing or still showing a placeholder. */
export async function pollMoney(locator: Locator): Promise<number> {
  const texts = await locator.allInnerTexts();
  return texts.length ? toMoney(texts[0]) : Number.NaN;
}

/** Sell every position and drop every non-default watchlist ticker, so a spec starts from
 *  known state instead of inheriting whatever the spec before it left behind. */
export async function resetState(): Promise<void> {
  const context = await request.newContext({ baseURL: BASE_URL });
  try {
    for (const held of (await getPortfolio(context)).positions) {
      const response = await context.post('/api/portfolio/trade', {
        data: { ticker: held.ticker, quantity: held.quantity, side: 'sell' },
      });
      expect(response.status(), await response.text()).toBe(200);
    }
    for (const entry of await getWatchlist(context)) {
      if (!DEFAULT_TICKERS.includes(entry.ticker)) {
        expect((await context.delete(`/api/watchlist/${entry.ticker}`)).ok()).toBeTruthy();
      }
    }
  } finally {
    await context.dispose();
  }
}

export function watchlistRows(page: Page): Locator {
  return page.locator('[data-testid^="watchlist-row-"]');
}

export function positionRows(page: Page): Locator {
  return page.locator('[data-testid^="position-row-"]');
}

export async function openApp(page: Page): Promise<void> {
  await page.goto('/');
  await expect(page.getByTestId('watchlist')).toBeVisible();
  await expect(page.getByTestId('connection-status')).toHaveAttribute('data-state', 'connected');
}

/** Every watchlist price cell joined together - a cheap way to detect any movement. */
export async function priceFingerprint(page: Page): Promise<string> {
  const prices = await page.locator('[data-testid^="watchlist-price-"]').allInnerTexts();
  return prices.join('|');
}

export async function expectPricesTicking(page: Page, timeout = 20_000): Promise<void> {
  const before = await priceFingerprint(page);
  await expect
    .poll(() => priceFingerprint(page), {
      timeout,
      message: 'watchlist prices never changed, so the SSE stream is not updating the UI',
    })
    .not.toBe(before);
}

export async function tradeViaUi(
  page: Page,
  ticker: string,
  quantity: number,
  side: 'buy' | 'sell',
): Promise<void> {
  await page.getByTestId('trade-ticker').fill(ticker);
  await page.getByTestId('trade-quantity').fill(String(quantity));
  await page.getByTestId(side === 'buy' ? 'trade-buy' : 'trade-sell').click();
}

export async function sendChat(page: Page, message: string): Promise<void> {
  const replies = page.locator('[data-testid^="chat-message-"][data-role="assistant"]');
  const before = await replies.count();
  await page.getByTestId('chat-input').fill(message);
  await page.getByTestId('chat-send').click();
  await expect(replies).toHaveCount(before + 1, { timeout: 30_000 });
  await expect(page.getByTestId('chat-loading')).toHaveCount(0);
}

export function lastAssistantMessage(page: Page): Locator {
  return page.locator('[data-testid^="chat-message-"][data-role="assistant"]').last();
}

export async function lastAssistantActions(request: APIRequestContext): Promise<ChatActions> {
  const messages = await getChatHistory(request);
  const assistant = messages.filter((m) => m.role === 'assistant');
  expect(assistant.length, 'no assistant message in /api/chat/history').toBeGreaterThan(0);
  return assistant[assistant.length - 1].actions;
}
