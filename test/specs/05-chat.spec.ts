import { expect, test } from '@playwright/test';
import {
  getPortfolio,
  getWatchlist,
  lastAssistantActions,
  lastAssistantMessage,
  openApp,
  resetState,
  sendChat,
} from './helpers';

// LLM_MOCK=true. Every expected reply below is taken verbatim from the mock rules in
// backend/app/llm/README.md: keyword match on the last user message, ticker = first
// upper-case 1-5 letter word, quantity = first number.
const ANALYSIS_REPLY = 'Your portfolio looks balanced. No action taken.';

test.describe.serial('AI chat', () => {
  test.beforeAll(resetState);

  test('a plain question is answered without touching the portfolio', async ({ page, request }) => {
    await openApp(page);
    const before = await getPortfolio(request);

    await sendChat(page, 'How is my portfolio looking today?');

    const user = page.locator('[data-testid^="chat-message-"][data-role="user"]').last();
    await expect(user).toContainText('How is my portfolio looking today?');
    await expect(lastAssistantMessage(page)).toContainText(ANALYSIS_REPLY);

    const actions = await lastAssistantActions(request);
    expect(actions?.trades ?? []).toHaveLength(0);
    expect(actions?.watchlist_changes ?? []).toHaveLength(0);

    const after = await getPortfolio(request);
    expect(after.cash_balance).toBe(before.cash_balance);
    expect(after.positions.map((p) => p.ticker)).toEqual(before.positions.map((p) => p.ticker));
  });

  test('asking to buy executes the trade and confirms it inline', async ({ page, request }) => {
    await openApp(page);
    const before = await getPortfolio(request);
    const heldBefore = before.positions.find((p) => p.ticker === 'NVDA')?.quantity ?? 0;

    await sendChat(page, 'buy 2 shares of NVDA for me');

    await expect(lastAssistantMessage(page)).toContainText('Buying 2 NVDA at market.');
    await expect(page.getByTestId('position-row-NVDA')).toBeVisible();

    const trades = (await lastAssistantActions(request))?.trades ?? [];
    expect(trades).toHaveLength(1);
    expect(trades[0].ticker).toBe('NVDA');
    expect(trades[0].side).toBe('buy');
    expect(trades[0].quantity).toBe(2);
    expect(trades[0].status, trades[0].error ?? '').toBe('executed');
    expect(trades[0].price).toBeGreaterThan(0);

    const after = await getPortfolio(request);
    expect(after.positions.find((p) => p.ticker === 'NVDA')?.quantity).toBeCloseTo(heldBefore + 2, 6);
    expect(after.cash_balance).toBeCloseTo(before.cash_balance - 2 * (trades[0].price ?? 0), 1);
  });

  test('asking to sell executes the sell', async ({ page, request }) => {
    await openApp(page);
    const before = await getPortfolio(request);
    const heldBefore = before.positions.find((p) => p.ticker === 'NVDA')?.quantity ?? 0;
    expect(heldBefore, 'the buy test should have left NVDA shares to sell').toBeGreaterThan(1);

    await sendChat(page, 'sell 1 share of NVDA');

    await expect(lastAssistantMessage(page)).toContainText('Selling 1 NVDA at market.');

    const trades = (await lastAssistantActions(request))?.trades ?? [];
    expect(trades).toHaveLength(1);
    expect(trades[0].ticker).toBe('NVDA');
    expect(trades[0].side).toBe('sell');
    expect(trades[0].quantity).toBe(1);
    expect(trades[0].status, trades[0].error ?? '').toBe('executed');

    const after = await getPortfolio(request);
    expect(after.positions.find((p) => p.ticker === 'NVDA')?.quantity).toBeCloseTo(heldBefore - 1, 6);
    expect(after.cash_balance).toBeCloseTo(before.cash_balance + (trades[0].price ?? 0), 1);
  });

  test('a trade the LLM cannot fill is reported as failed', async ({ page, request }) => {
    await openApp(page);
    const before = await getPortfolio(request);

    await sendChat(page, 'buy 100000 NVDA');

    // The mock's message is fixed; the failure has to surface in the action, not the text.
    await expect(lastAssistantMessage(page)).toContainText('Buying 100000 NVDA at market.');

    const trades = (await lastAssistantActions(request))?.trades ?? [];
    expect(trades).toHaveLength(1);
    expect(trades[0].status).toBe('failed');
    expect(trades[0].error ?? '').not.toBe('');

    const after = await getPortfolio(request);
    expect(after.cash_balance).toBe(before.cash_balance);
  });

  test('asking to watch a ticker adds it to the watchlist', async ({ page, request }) => {
    await openApp(page);
    const before = (await getWatchlist(request)).map((entry) => entry.ticker);
    expect(before).not.toContain('PLTR');

    await sendChat(page, 'watch PLTR for me');

    await expect(lastAssistantMessage(page)).toContainText('Added PLTR to your watchlist.');
    await expect(page.getByTestId('watchlist-row-PLTR')).toBeVisible();

    const changes = (await lastAssistantActions(request))?.watchlist_changes ?? [];
    expect(changes).toHaveLength(1);
    expect(changes[0].ticker).toBe('PLTR');
    expect(changes[0].action).toBe('add');
    expect(changes[0].status, changes[0].error ?? '').toBe('executed');

    const after = (await getWatchlist(request)).map((entry) => entry.ticker);
    expect(after).toContain('PLTR');
    expect(after).toHaveLength(before.length + 1);
  });

  test('the conversation survives a reload', async ({ page, request }) => {
    const response = await request.get('/api/chat/history');
    expect(response.ok()).toBeTruthy();
    const messages = (await response.json()).messages as { role: string; content: string }[];
    // Five exchanges above; chat history has no reset endpoint, so this is a floor.
    expect(messages.length).toBeGreaterThanOrEqual(10);
    expect(messages[0].role).toBe('user');
    expect(messages[1].content).toContain(ANALYSIS_REPLY);

    await openApp(page);
    await expect(page.locator('[data-testid^="chat-message-"]')).toHaveCount(messages.length);
  });
});
