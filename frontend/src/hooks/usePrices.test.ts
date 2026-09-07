import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { usePrices } from "./usePrices";

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;

  readyState = FakeEventSource.CONNECTING;
  closed = false;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;

  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }

  open() {
    this.readyState = FakeEventSource.OPEN;
    this.onopen?.();
  }

  emit(payload: unknown) {
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(payload) }));
  }

  fail(readyState: number) {
    this.readyState = readyState;
    this.onerror?.();
  }

  close() {
    this.closed = true;
    this.readyState = FakeEventSource.CLOSED;
  }
}

const frame = (ticker: string, price: number, timestamp: number) => ({
  [ticker]: {
    ticker,
    price,
    previous_price: price - 1,
    timestamp,
    change: 1,
    change_percent: 0.5,
    direction: "up" as const,
  },
});

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const latest = () =>
  FakeEventSource.instances[FakeEventSource.instances.length - 1];

describe("usePrices", () => {
  it("subscribes to the price stream once", () => {
    renderHook(() => usePrices());
    expect(FakeEventSource.instances).toHaveLength(1);
    expect(latest().url).toContain("/api/stream/prices");
  });

  it("reports connected on open and the right state on failure", () => {
    const { result } = renderHook(() => usePrices());
    expect(result.current.status).toBe("reconnecting");

    act(() => latest().open());
    expect(result.current.status).toBe("connected");

    act(() => latest().fail(FakeEventSource.CONNECTING));
    expect(result.current.status).toBe("reconnecting");

    act(() => latest().fail(FakeEventSource.CLOSED));
    expect(result.current.status).toBe("disconnected");
  });

  it("leaves connected when the stream drops and returns on recovery", () => {
    const { result } = renderHook(() => usePrices());

    act(() => latest().open());
    expect(result.current.status).toBe("connected");

    // A dropped stream leaves readyState at CONNECTING while it retries.
    act(() => latest().fail(FakeEventSource.CONNECTING));
    expect(result.current.status).toBe("reconnecting");

    act(() => latest().open());
    expect(result.current.status).toBe("connected");
    expect(FakeEventSource.instances).toHaveLength(1);
  });

  it("stores the latest price and accumulates history per ticker", () => {
    const { result } = renderHook(() => usePrices());

    act(() => latest().emit(frame("AAPL", 190, 1)));
    act(() => latest().emit(frame("AAPL", 191, 2)));
    act(() => latest().emit(frame("MSFT", 400, 3)));

    expect(result.current.prices.AAPL.price).toBe(191);
    expect(result.current.prices.MSFT.price).toBe(400);
    expect(result.current.history.AAPL).toEqual([
      { t: 1, price: 190 },
      { t: 2, price: 191 },
    ]);
    expect(result.current.history.MSFT).toEqual([{ t: 3, price: 400 }]);
  });

  it("ignores malformed frames", () => {
    const { result } = renderHook(() => usePrices());
    act(() => latest().emit(frame("AAPL", 190, 1)));
    act(() => latest().onmessage?.(new MessageEvent("message", { data: "{oops" })));

    expect(result.current.history.AAPL).toHaveLength(1);
  });

  it("closes the stream on unmount", () => {
    const { unmount } = renderHook(() => usePrices());
    const source = latest();
    unmount();
    expect(source.closed).toBe(true);
  });
});
