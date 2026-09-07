import { expect, test } from '@playwright/test';
import {
  DEFAULT_TICKERS,
  getWatchlist,
  openApp,
  pollMoney,
  resetState,
  watchlistRows,
} from './helpers';

const NEW_TICKER = 'PYPL';

test.describe.serial('watchlist', () => {
  test.beforeAll(resetState);

  test('adding a ticker puts it on the list and starts pricing it', async ({ page, request }) => {
    await openApp(page);
    const before = await watchlistRows(page).count();

    // Lower case on purpose: the API normalises to upper case.
    await page.getByTestId('watchlist-add-input').fill(NEW_TICKER.toLowerCase());
    await page.getByTestId('watchlist-add-submit').click();

    await expect(page.getByTestId(`watchlist-row-${NEW_TICKER}`)).toBeVisible();
    await expect(watchlistRows(page)).toHaveCount(before + 1);

    const tickers = (await getWatchlist(request)).map((entry) => entry.ticker);
    expect(tickers).toContain(NEW_TICKER);

    // The cell shows a placeholder until the stream delivers, so this must be poll-safe.
    await expect
      .poll(() => pollMoney(page.getByTestId(`watchlist-price-${NEW_TICKER}`)), {
        message: `${NEW_TICKER} was added but never received a price`,
      })
      .toBeGreaterThan(0);
  });

  test('the API rejects a ticker that is already watched', async ({ request }) => {
    const response = await request.post('/api/watchlist', { data: { ticker: DEFAULT_TICKERS[0] } });
    expect(response.status()).toBe(409);
  });

  test('removing a ticker takes it off the list', async ({ page, request }) => {
    await openApp(page);
    const before = await watchlistRows(page).count();

    await page.getByTestId(`watchlist-remove-${NEW_TICKER}`).click();

    await expect(page.getByTestId(`watchlist-row-${NEW_TICKER}`)).toHaveCount(0);
    await expect(watchlistRows(page)).toHaveCount(before - 1);

    const tickers = (await getWatchlist(request)).map((entry) => entry.ticker);
    expect(tickers).not.toContain(NEW_TICKER);
    expect(tickers).toEqual(DEFAULT_TICKERS);
  });
});
