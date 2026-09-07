import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Watchlist } from "./Watchlist";
import { priceMap, watchlistEntry } from "@/test/fixtures";

const tickers = [watchlistEntry("AAPL", 190), watchlistEntry("MSFT", 400)];

function renderWatchlist(overrides: Partial<Parameters<typeof Watchlist>[0]> = {}) {
  const props = {
    tickers,
    prices: priceMap({ AAPL: 190, MSFT: 400 }),
    history: {},
    selected: "AAPL",
    onSelect: vi.fn(),
    onAdd: vi.fn(),
    onRemove: vi.fn(),
    error: null,
    ...overrides,
  };
  return { props, ...render(<Watchlist {...props} />) };
}

afterEach(() => vi.useRealTimers());

describe("Watchlist", () => {
  it("renders a row per ticker with its price", () => {
    renderWatchlist();
    expect(screen.getByTestId("watchlist")).toBeInTheDocument();
    expect(screen.getByTestId("watchlist-row-AAPL")).toBeInTheDocument();
    expect(screen.getByTestId("watchlist-price-MSFT")).toHaveTextContent("400.00");
  });

  it("shows session change measured from the first observed price", () => {
    renderWatchlist({
      prices: priceMap({ AAPL: 199.5, MSFT: 400 }),
      history: { AAPL: [{ t: 1, price: 190 }, { t: 2, price: 199.5 }] },
    });
    expect(screen.getByTestId("watchlist-row-AAPL")).toHaveTextContent("+5.00%");
  });

  it("flashes on an uptick and clears the flash after 500ms", () => {
    vi.useFakeTimers();
    const { rerender, props } = renderWatchlist();
    const cell = () => screen.getByTestId("watchlist-price-AAPL");
    expect(cell().className).not.toMatch(/flash/);

    rerender(
      <Watchlist {...props} prices={priceMap({ AAPL: 191, MSFT: 400 })} />,
    );
    expect(cell()).toHaveClass("flash-up");

    act(() => vi.advanceTimersByTime(500));
    expect(cell().className).not.toMatch(/flash/);
  });

  it("flashes down on a downtick", () => {
    vi.useFakeTimers();
    const { rerender, props } = renderWatchlist();
    rerender(
      <Watchlist {...props} prices={priceMap({ AAPL: 189, MSFT: 400 })} />,
    );
    expect(screen.getByTestId("watchlist-price-AAPL")).toHaveClass("flash-down");
  });

  it("adds a ticker in upper case and clears the input", async () => {
    const user = userEvent.setup();
    const { props } = renderWatchlist();

    await user.type(screen.getByTestId("watchlist-add-input"), "pypl");
    await user.click(screen.getByTestId("watchlist-add-submit"));

    expect(props.onAdd).toHaveBeenCalledWith("PYPL");
    expect(screen.getByTestId("watchlist-add-input")).toHaveValue("");
  });

  it("ignores an empty add", async () => {
    const user = userEvent.setup();
    const { props } = renderWatchlist();
    await user.click(screen.getByTestId("watchlist-add-submit"));
    expect(props.onAdd).not.toHaveBeenCalled();
  });

  it("removes a ticker without selecting the row", async () => {
    const user = userEvent.setup();
    const { props } = renderWatchlist();

    await user.click(screen.getByTestId("watchlist-remove-MSFT"));

    expect(props.onRemove).toHaveBeenCalledWith("MSFT");
    expect(props.onSelect).not.toHaveBeenCalled();
  });

  it("selects a ticker when its row is clicked", async () => {
    const user = userEvent.setup();
    const { props } = renderWatchlist();
    await user.click(screen.getByTestId("watchlist-row-MSFT"));
    expect(props.onSelect).toHaveBeenCalledWith("MSFT");
  });

  it("surfaces a watchlist error", () => {
    renderWatchlist({ error: "Ticker already on the watchlist" });
    expect(screen.getByText("Ticker already on the watchlist")).toBeInTheDocument();
  });
});
