import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Workstation from "./page";
import { chatHistory, portfolio, watchlistEntry } from "@/test/fixtures";

const watchlist = [watchlistEntry("AAPL", 193.5), watchlistEntry("TSLA", 240)];

let streams: FakeEventSource[] = [];

class FakeEventSource {
  readyState = 0;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;

  constructor() {
    streams.push(this);
  }

  push(prices: Record<string, number>) {
    const frame = Object.fromEntries(
      Object.entries(prices).map(([ticker, price]) => [
        ticker,
        {
          ticker,
          price,
          previous_price: price,
          timestamp: Date.now() / 1000,
          change: 0,
          change_percent: 0,
          direction: "flat",
        },
      ]),
    );
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(frame) }));
  }

  close() {}
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status });

let routes: Record<string, () => Response>;

beforeEach(() => {
  streams = [];
  routes = {
    "GET /api/watchlist": () => json({ tickers: watchlist }),
    "GET /api/portfolio": () => json(portfolio),
    "GET /api/portfolio/history": () => json({ snapshots: [] }),
    "GET /api/chat/history": () => json({ messages: chatHistory }),
  };

  vi.stubGlobal("EventSource", FakeEventSource);
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      const route = routes[`${init?.method ?? "GET"} ${url}`];
      if (!route) throw new Error(`unstubbed route: ${init?.method} ${url}`);
      return Promise.resolve(route());
    }),
  );
});

afterEach(() => vi.unstubAllGlobals());

describe("Workstation", () => {
  it("loads the watchlist, portfolio and chat history on mount", async () => {
    render(<Workstation />);

    expect(await screen.findByTestId("watchlist-row-AAPL")).toBeInTheDocument();
    expect(screen.getByTestId("cash-balance")).toHaveTextContent("$8,080.00");
    expect(screen.getByTestId("total-value")).toHaveTextContent("$10,975.00");
    expect(screen.getByTestId("position-row-TSLA")).toBeInTheDocument();
    expect(screen.getByTestId("chat-message-1")).toHaveTextContent(
      "Bought 10 AAPL",
    );
  });

  it("renders exactly the persisted chat history, actions included", async () => {
    render(<Workstation />);
    await screen.findByTestId("chat-message-0");

    // A reload must show the stored messages and nothing more.
    expect(screen.getAllByTestId(/^chat-message-\d+$/)).toHaveLength(
      chatHistory.length,
    );
    expect(screen.queryByTestId(`chat-message-${chatHistory.length}`)).toBeNull();
    expect(screen.getByTestId("chat-message-1")).toHaveTextContent(
      "BUY 10 AAPL @ 192.00",
    );
  });

  it("selects the first watchlist ticker for the main chart and trade bar", async () => {
    render(<Workstation />);

    await waitFor(() =>
      expect(screen.getByTestId("main-chart")).toHaveAttribute(
        "data-ticker",
        "AAPL",
      ),
    );
    expect(screen.getByTestId("trade-ticker")).toHaveValue("AAPL");
  });

  it("revalues the header total from the price stream", async () => {
    render(<Workstation />);
    await screen.findByTestId("watchlist-row-AAPL");

    act(() => streams[0].push({ AAPL: 200, TSLA: 240 }));

    // 8080 cash + 10 * 200 + 4 * 240
    expect(screen.getByTestId("total-value")).toHaveTextContent("$11,040.00");
    expect(screen.getByTestId("watchlist-price-AAPL")).toHaveTextContent("200.00");
  });

  it("reflects the connection state of the stream", async () => {
    render(<Workstation />);
    expect(screen.getByTestId("connection-status")).toHaveAttribute(
      "data-state",
      "reconnecting",
    );

    act(() => {
      streams[0].readyState = 1;
      streams[0].onopen?.();
    });
    expect(screen.getByTestId("connection-status")).toHaveAttribute(
      "data-state",
      "connected",
    );
  });

  it("applies the portfolio returned by a trade", async () => {
    const traded = { ...portfolio, cash_balance: 6145.0 };
    routes["POST /api/portfolio/trade"] = () =>
      json({ trade: {}, portfolio: traded });

    const user = userEvent.setup();
    render(<Workstation />);
    await screen.findByTestId("watchlist-row-AAPL");

    await user.click(screen.getByTestId("trade-buy"));

    await waitFor(() =>
      expect(screen.getByTestId("cash-balance")).toHaveTextContent("$6,145.00"),
    );
    expect(screen.queryByTestId("trade-error")).not.toBeInTheDocument();
  });

  it("shows the rejection message when a trade fails", async () => {
    routes["POST /api/portfolio/trade"] = () =>
      json({ detail: "Insufficient cash" }, 400);

    const user = userEvent.setup();
    render(<Workstation />);
    await screen.findByTestId("watchlist-row-AAPL");

    await user.click(screen.getByTestId("trade-buy"));

    expect(await screen.findByTestId("trade-error")).toHaveTextContent(
      "Insufficient cash",
    );
  });

  it("appends the user message, then the assistant reply with its actions", async () => {
    routes["POST /api/chat"] = () =>
      json({
        message: "Bought 1 NVDA.",
        trades: [
          {
            ticker: "NVDA",
            side: "buy",
            quantity: 1,
            status: "executed",
            price: 120.0,
            error: null,
          },
        ],
        watchlist_changes: [],
        portfolio,
      });

    const user = userEvent.setup();
    render(<Workstation />);
    await screen.findByTestId("watchlist-row-AAPL");

    await user.type(screen.getByTestId("chat-input"), "buy 1 nvda");
    await user.click(screen.getByTestId("chat-send"));

    expect(await screen.findByTestId("chat-message-2")).toHaveTextContent(
      "buy 1 nvda",
    );
    const reply = await screen.findByTestId("chat-message-3");
    expect(reply).toHaveAttribute("data-role", "assistant");
    expect(reply).toHaveTextContent("BUY 1 NVDA @ 120.00");
  });

  it("adds and removes watchlist tickers", async () => {
    const added = [...watchlist, watchlistEntry("PYPL", 70)];
    routes["POST /api/watchlist"] = () => json({ tickers: added }, 201);
    routes["DELETE /api/watchlist/TSLA"] = () =>
      json({ tickers: [watchlistEntry("AAPL", 193.5)] });

    const user = userEvent.setup();
    render(<Workstation />);
    await screen.findByTestId("watchlist-row-AAPL");

    await user.type(screen.getByTestId("watchlist-add-input"), "pypl");
    await user.click(screen.getByTestId("watchlist-add-submit"));
    expect(await screen.findByTestId("watchlist-row-PYPL")).toBeInTheDocument();

    await user.click(screen.getByTestId("watchlist-remove-TSLA"));
    await waitFor(() =>
      expect(screen.queryByTestId("watchlist-row-TSLA")).not.toBeInTheDocument(),
    );
  });

  it("reports an add that the backend rejects", async () => {
    routes["POST /api/watchlist"] = () =>
      json({ detail: "Ticker already on the watchlist" }, 409);

    const user = userEvent.setup();
    render(<Workstation />);
    await screen.findByTestId("watchlist-row-AAPL");

    await user.type(screen.getByTestId("watchlist-add-input"), "aapl");
    await user.click(screen.getByTestId("watchlist-add-submit"));

    expect(
      await screen.findByText("Ticker already on the watchlist"),
    ).toBeInTheDocument();
  });
});
