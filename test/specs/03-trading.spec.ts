import { expect, test } from '@playwright/test';
import {
  getPortfolio,
  getWatchlist,
  openApp,
  position,
  pollMoney,
  positionRows,
  readMoney,
  resetState,
  tradeViaUi,
} from './helpers';

const TICKER = 'AAPL';
const BUY_QTY = 5;
const PARTIAL_SELL_QTY = 2;

test.describe.serial('trading', () => {
  test.beforeAll(resetState);

  test('a buy fills instantly: cash falls and the position appears', async ({ page, request }) => {
    await openApp(page);
    const before = await getPortfolio(request);
    expect(await readMoney(page.getByTestId('cash-balance'))).toBeCloseTo(before.cash_balance, 1);

    await tradeViaUi(page, TICKER, BUY_QTY, 'buy');

    await expect(page.getByTestId(`position-row-${TICKER}`)).toBeVisible();
    await expect(page.getByTestId(`position-row-${TICKER}`)).toContainText(TICKER);
    await expect(page.getByTestId('trade-error')).toHaveCount(0);

    const after = await getPortfolio(request);
    const held = position(after, TICKER);
    expect(held.quantity).toBe(BUY_QTY);
    expect(held.avg_cost).toBeGreaterThan(0);
    expect(after.cash_balance).toBeCloseTo(before.cash_balance - BUY_QTY * held.avg_cost, 1);
    expect(after.positions_value).toBeCloseTo(held.quantity * held.current_price, 1);
    expect(after.total_value).toBeCloseTo(after.cash_balance + after.positions_value, 1);

    // The header must catch up with the new balance.
    await expect
      .poll(() => pollMoney(page.getByTestId('cash-balance')), {
        message: 'the header cash balance did not follow the trade',
      })
      .toBeCloseTo(after.cash_balance, 1);
  });

  test('a partial sell returns cash and shrinks the position', async ({ page, request }) => {
    await openApp(page);
    const before = await getPortfolio(request);
    const heldBefore = position(before, TICKER);

    await tradeViaUi(page, TICKER, PARTIAL_SELL_QTY, 'sell');

    await expect
      .poll(() => pollMoney(page.getByTestId('cash-balance')), {
        message: 'the header cash balance did not rise after the sell',
      })
      .toBeGreaterThan(before.cash_balance);

    const after = await getPortfolio(request);
    const heldAfter = position(after, TICKER);
    expect(heldAfter.quantity).toBeCloseTo(heldBefore.quantity - PARTIAL_SELL_QTY, 6);
    // A sale never re-prices the remaining lot.
    expect(heldAfter.avg_cost).toBeCloseTo(heldBefore.avg_cost, 2);

    // Prices move continuously, so bound the proceeds rather than fixing them.
    const proceeds = after.cash_balance - before.cash_balance;
    const reference = PARTIAL_SELL_QTY * heldBefore.current_price;
    expect(proceeds).toBeGreaterThan(reference * 0.9);
    expect(proceeds).toBeLessThan(reference * 1.1);
  });

  test('selling the remainder removes the position', async ({ page, request }) => {
    await openApp(page);
    const before = await getPortfolio(request);
    const heldBefore = position(before, TICKER);

    await tradeViaUi(page, TICKER, heldBefore.quantity, 'sell');

    await expect(page.getByTestId(`position-row-${TICKER}`)).toHaveCount(0);
    await expect(positionRows(page)).toHaveCount(0);

    const after = await getPortfolio(request);
    expect(after.positions).toEqual([]);
    expect(after.positions_value).toBe(0);
    expect(after.cash_balance).toBeGreaterThan(before.cash_balance);
    expect(after.total_value).toBeCloseTo(after.cash_balance, 2);
  });

  test('a trade that cannot fill is rejected and changes nothing', async ({ page, request }) => {
    await openApp(page);
    const before = await getPortfolio(request);

    await tradeViaUi(page, TICKER, 100_000, 'buy');

    const error = page.getByTestId('trade-error');
    await expect(error).toBeVisible();
    expect((await error.innerText()).trim()).not.toBe('');
    await expect(page.getByTestId(`position-row-${TICKER}`)).toHaveCount(0);

    const after = await getPortfolio(request);
    expect(after.cash_balance).toBe(before.cash_balance);
    expect(after.positions).toEqual([]);
  });

  test('selling shares that are not held is rejected', async ({ page, request }) => {
    await openApp(page);
    const before = await getPortfolio(request);

    await tradeViaUi(page, 'TSLA', 3, 'sell');

    await expect(page.getByTestId('trade-error')).toBeVisible();

    const after = await getPortfolio(request);
    expect(after.cash_balance).toBe(before.cash_balance);
    expect(after.positions).toEqual([]);
  });

  // CONTRACTS.md sections 2 and 3: DELETE keeps the price feed running for a ticker we
  // hold, so it leaves the watchlist but stays priced, and the next buy fills and puts it
  // back. This is the only path that reaches the "a buy adds an unwatched ticker" rule -
  // a first-ever buy of a never-watched ticker has no cached price and is rejected.
  test('buying a held but unwatched ticker puts it back on the watchlist', async ({
    page,
    request,
  }) => {
    await openApp(page);
    await tradeViaUi(page, TICKER, 1, 'buy');
    await expect(page.getByTestId(`position-row-${TICKER}`)).toBeVisible();

    expect((await request.delete(`/api/watchlist/${TICKER}`)).status()).toBe(200);
    expect((await getWatchlist(request)).map((entry) => entry.ticker)).not.toContain(TICKER);

    await openApp(page);
    await expect(page.getByTestId(`watchlist-row-${TICKER}`)).toHaveCount(0);
    await expect(page.getByTestId(`position-row-${TICKER}`)).toBeVisible();

    // Still priced, because the position is open.
    const priceAtRemoval = position(await getPortfolio(request), TICKER).current_price;
    await expect
      .poll(async () => position(await getPortfolio(request), TICKER).current_price, {
        timeout: 20_000,
        message: `${TICKER} stopped being priced after it left the watchlist`,
      })
      .not.toBe(priceAtRemoval);

    await tradeViaUi(page, TICKER, 1, 'buy');
    await expect(page.getByTestId('trade-error')).toHaveCount(0);
    await expect
      .poll(async () => (await getWatchlist(request)).map((entry) => entry.ticker), {
        message: `the second buy did not put ${TICKER} back on the watchlist`,
      })
      .toContain(TICKER);

    await openApp(page);
    await expect(page.getByTestId(`watchlist-row-${TICKER}`)).toBeVisible();

    // Leave the portfolio flat for the specs that follow.
    const held = position(await getPortfolio(request), TICKER).quantity;
    await tradeViaUi(page, TICKER, held, 'sell');
    await expect(positionRows(page)).toHaveCount(0);
    expect((await getPortfolio(request)).positions).toEqual([]);
  });
});
