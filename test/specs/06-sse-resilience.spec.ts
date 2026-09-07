import net from 'node:net';
import { expect, test, type Locator, type Page } from '@playwright/test';
import { BASE_URL, priceFingerprint, resetState } from './helpers';

// context.setOffline does not sever an SSE response that is already streaming - verified
// against the running app: prices kept arriving and the status dot stayed connected. So
// the browser reaches the app through a TCP proxy this test owns, and the interruption is
// a real socket destroy. The proxy listens on 127.0.0.1, which also keeps Chrome from
// upgrading the navigation to https.
type Proxy = { url: string; cut: () => void; close: () => Promise<void> };

async function startProxy(target: URL): Promise<Proxy> {
  const port = Number(target.port || 80);
  const live = new Set<net.Socket>();

  const server = net.createServer((client) => {
    const upstream = net.connect(port, target.hostname);
    for (const socket of [client, upstream]) {
      live.add(socket);
      socket.on('error', () => socket.destroy());
      socket.on('close', () => live.delete(socket));
    }
    client.pipe(upstream);
    upstream.pipe(client);
  });

  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const listening = server.address() as net.AddressInfo;

  return {
    url: `http://127.0.0.1:${listening.port}`,
    cut: () => {
      for (const socket of live) socket.destroy();
      live.clear();
    },
    close: () =>
      new Promise<void>((resolve) => {
        for (const socket of live) socket.destroy();
        live.clear();
        server.close(() => resolve());
      }),
  };
}

async function expectTicking(page: Page, timeout = 30_000): Promise<void> {
  const before = await priceFingerprint(page);
  await expect
    .poll(() => priceFingerprint(page), { timeout, message: 'prices stopped updating' })
    .not.toBe(before);
}

async function reachesConnected(status: Locator, timeout: number): Promise<boolean> {
  try {
    await expect(status).toHaveAttribute('data-state', 'connected', { timeout });
    return true;
  } catch {
    return false;
  }
}

test.describe('SSE resilience', () => {
  test.beforeAll(resetState);

  test('prices resume after the price stream is cut', async ({ page }) => {
    const proxy = await startProxy(new URL(BASE_URL));
    try {
      await page.goto(proxy.url + '/');
      await expect(page.getByTestId('watchlist')).toBeVisible();
      const status = page.getByTestId('connection-status');
      await expect(status).toHaveAttribute('data-state', 'connected');
      await expectTicking(page);

      proxy.cut();
      await expect(status).not.toHaveAttribute('data-state', 'connected', { timeout: 30_000 });

      // EventSource retries on its own while it is still CONNECTING; once the browser has
      // closed the socket for good only a reload gets it back. Either route counts as
      // recovery, never reaching connected does not.
      if (!(await reachesConnected(status, 20_000))) {
        await page.reload();
        await expect(page.getByTestId('watchlist')).toBeVisible();
        await expect(status).toHaveAttribute('data-state', 'connected', { timeout: 30_000 });
      }

      await expectTicking(page);
    } finally {
      await proxy.close();
    }
  });
});
