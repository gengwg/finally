import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, addWatchlistTicker, executeTrade, getPortfolio } from "./api";
import { portfolio } from "@/test/fixtures";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status });

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("unwraps a portfolio response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(portfolio)));
    await expect(getPortfolio()).resolves.toEqual(portfolio);
  });

  it("posts a trade as JSON", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(json({ trade: {}, portfolio }));
    vi.stubGlobal("fetch", fetchMock);

    await executeTrade("AAPL", 10, "buy");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/portfolio/trade");
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(init.body)).toEqual({
      ticker: "AAPL",
      quantity: 10,
      side: "buy",
    });
  });

  it("raises the API detail message on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(json({ detail: "Insufficient cash" }, 400)),
    );

    await expect(executeTrade("AAPL", 1e6, "buy")).rejects.toThrow(
      "Insufficient cash",
    );
  });

  it("falls back to the status code when there is no detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("nope", { status: 500 })),
    );

    await expect(addWatchlistTicker("PYPL")).rejects.toBeInstanceOf(ApiError);
    await expect(addWatchlistTicker("PYPL")).rejects.toThrow(
      "Request failed (500)",
    );
  });
});
