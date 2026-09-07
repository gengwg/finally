import { expect, test } from '@playwright/test';
import {
  getPortfolio,
  getSnapshots,
  openApp,
  position,
  positionRows,
  resetState,
} from './helpers';

const HOLDINGS: [string, number][] = [
  ['MSFT', 3],
  ['NVDA', 2],
];

function pnlSign(value: number): 'profit' | 'loss' | 'flat' {
  if (value > 0) return 'profit';
  if (value < 0) return 'loss';
  return 'flat';
}

// Not serial: every test here depends only on the holdings the first one establishes, so
// a failure in one should not hide the others.
test.describe('portfolio visualisations', () => {
  test.beforeAll(resetState);

  test('each trade records a portfolio snapshot', async ({ request }) => {
    const before = await getSnapshots(request);

    for (const [ticker, quantity] of HOLDINGS) {
      const response = await request.post('/api/portfolio/trade', {
        data: { ticker, quantity, side: 'buy' },
      });
      expect(response.status(), await response.text()).toBe(200);
    }

    const after = await getSnapshots(request);
    expect(after.length).toBeGreaterThanOrEqual(before.length + HOLDINGS.length);
    expect(after[after.length - 1].total_value).toBeGreaterThan(0);
    // Oldest first, per the contract.
    const timestamps = after.map((snapshot) => snapshot.recorded_at);
    expect([...timestamps].sort()).toEqual(timestamps);
  });

  test('the heatmap draws one tile per position, keyed to its P&L', async ({ page, request }) => {
    await openApp(page);

    const portfolio = await getPortfolio(request);
    expect(portfolio.positions.length).toBe(HOLDINGS.length);
    for (const [ticker, quantity] of HOLDINGS) {
      expect(position(portfolio, ticker).quantity).toBe(quantity);
      await expect(page.getByTestId(`position-row-${ticker}`)).toBeVisible();
    }
    await expect(positionRows(page)).toHaveCount(HOLDINGS.length);

    const heatmap = page.getByTestId('heatmap');
    await expect(heatmap).toBeVisible();
    await expect(page.locator('[data-testid^="heatmap-tile-"]')).toHaveCount(HOLDINGS.length);

    for (const [ticker] of HOLDINGS) {
      const tile = page.getByTestId(`heatmap-tile-${ticker}`);
      await expect(tile).toBeVisible();
      await expect(tile).toHaveAttribute('data-pnl', /^(profit|loss|flat)$/);

      // The sign is asserted, never the colour, so a palette change cannot break this.
      // Polled because the tile follows the live price while the API read is a snapshot.
      await expect
        .poll(
          async () => {
            const pnl = position(await getPortfolio(request), ticker).unrealized_pnl;
            const rendered = await tile.getAttribute('data-pnl');
            return rendered === pnlSign(pnl) ? 'agrees' : `tile says ${rendered}, P&L is ${pnl}`;
          },
          { message: `the ${ticker} heatmap tile never agreed with its unrealized P&L` },
        )
        .toBe('agrees');
    }

    const box = await heatmap.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThan(0);
    expect(box?.height ?? 0).toBeGreaterThan(0);
  });

  test('the P&L chart renders the recorded portfolio history', async ({ page, request }) => {
    await openApp(page);
    expect((await getSnapshots(request)).length).toBeGreaterThan(0);

    const chart = page.getByTestId('pnl-chart');
    await expect(chart).toBeVisible();
    // Drawn content, not just an empty container.
    await expect
      .poll(() => chart.locator('canvas, svg').count(), {
        message: 'pnl-chart rendered no chart content',
      })
      .toBeGreaterThan(0);

    const box = await chart.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThan(0);
    expect(box?.height ?? 0).toBeGreaterThan(0);
  });

  test('selecting a watchlist ticker loads it into the main chart', async ({ page }) => {
    await openApp(page);
    await page.getByTestId('watchlist-row-TSLA').click();
    await expect(page.getByTestId('main-chart')).toHaveAttribute('data-ticker', 'TSLA');
  });
});
