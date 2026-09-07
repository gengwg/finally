import { expect, test } from '@playwright/test';
import {
  DEFAULT_TICKERS,
  expectPricesTicking,
  getPortfolio,
  openApp,
  readMoney,
  toMoney,
  watchlistRows,
} from './helpers';

// Runs first, against an untouched database: nothing has traded yet.
test('a fresh install shows the default watchlist, $10,000 and streaming prices', async ({
  page,
  request,
}) => {
  await openApp(page);

  await expect(watchlistRows(page)).toHaveCount(DEFAULT_TICKERS.length);
  for (const ticker of DEFAULT_TICKERS) {
    await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible();
  }

  expect(await readMoney(page.getByTestId('cash-balance'))).toBe(10_000);
  expect(await readMoney(page.getByTestId('total-value'))).toBeCloseTo(10_000, 1);

  const portfolio = await getPortfolio(request);
  expect(portfolio.cash_balance).toBe(10_000);
  expect(portfolio.positions).toEqual([]);
  expect(portfolio.total_value).toBeCloseTo(10_000, 2);

  // Every ticker gets a real price...
  await expect
    .poll(
      async () => {
        const cells = await page.locator('[data-testid^="watchlist-price-"]').allInnerTexts();
        return cells.filter((text) => toMoney(text) > 0).length;
      },
      { message: 'not every watchlist row received a price from the stream' },
    )
    .toBe(DEFAULT_TICKERS.length);

  // ...and those prices then move.
  await expectPricesTicking(page);
});
