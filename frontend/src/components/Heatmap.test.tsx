import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Heatmap, pnlSign } from "./Heatmap";
import { giveLayout } from "@/test/layout";
import type { PositionView } from "@/lib/types";

const position = (
  ticker: string,
  unrealized_pnl: number,
  pnl_percent: number,
): PositionView => ({
  ticker,
  quantity: 10,
  avg_cost: 100,
  current_price: 100 + pnl_percent,
  market_value: 1000,
  unrealized_pnl,
  pnl_percent,
});

let restore: (() => void) | null = null;

afterEach(() => {
  restore?.();
  restore = null;
});

describe("pnlSign", () => {
  it("maps the P&L sign in all three directions", () => {
    expect(pnlSign(15)).toBe("profit");
    expect(pnlSign(-40)).toBe("loss");
    expect(pnlSign(0)).toBe("flat");
  });
});

const tiles = () =>
  document.querySelectorAll('[data-testid^="heatmap-tile-"]');

describe("Heatmap", () => {
  it("renders exactly one tile per position and no others", () => {
    restore = giveLayout();
    // Recharts renders content for its synthetic root too; only leaves are positions.
    const { rerender } = render(<Heatmap positions={[position("MSFT", 5, 1)]} />);
    expect(tiles()).toHaveLength(1);

    rerender(
      <Heatmap
        positions={[position("MSFT", 5, 1), position("NVDA", -2, -1)]}
      />,
    );
    expect(tiles()).toHaveLength(2);
    expect([...tiles()].map((tile) => tile.getAttribute("data-testid"))).toEqual([
      "heatmap-tile-MSFT",
      "heatmap-tile-NVDA",
    ]);

    rerender(
      <Heatmap
        positions={[
          position("MSFT", 5, 1),
          position("NVDA", -2, -1),
          position("AAPL", 3, 0.5),
          position("TSLA", -9, -4),
        ]}
      />,
    );
    expect(tiles()).toHaveLength(4);
  });

  it("renders a tile per position tagged with its P&L direction", () => {
    restore = giveLayout();
    render(
      <Heatmap
        positions={[
          position("AAPL", 15, 0.78),
          position("TSLA", -40, -4),
          position("JPM", 0, 0),
        ]}
      />,
    );

    expect(screen.getByTestId("heatmap-tile-AAPL")).toHaveAttribute(
      "data-pnl",
      "profit",
    );
    expect(screen.getByTestId("heatmap-tile-TSLA")).toHaveAttribute(
      "data-pnl",
      "loss",
    );
    expect(screen.getByTestId("heatmap-tile-JPM")).toHaveAttribute(
      "data-pnl",
      "flat",
    );
  });

  it("colours the tile from the same sign it reports", () => {
    restore = giveLayout();
    render(
      <Heatmap positions={[position("AAPL", 15, 0.78), position("TSLA", -40, -4)]} />,
    );

    const fill = (ticker: string) =>
      screen
        .getByTestId(`heatmap-tile-${ticker}`)
        .querySelector("rect")
        ?.getAttribute("fill");

    expect(fill("AAPL")).toContain("--color-up");
    expect(fill("TSLA")).toContain("--color-down");
  });

  it("sizes tiles by market value", () => {
    restore = giveLayout();
    const big = { ...position("NVDA", 100, 10), market_value: 4000 };
    const small = { ...position("V", 10, 1), market_value: 1000 };
    render(<Heatmap positions={[big, small]} />);

    const area = (ticker: string) => {
      const rect = screen
        .getByTestId(`heatmap-tile-${ticker}`)
        .querySelector("rect")!;
      return (
        Number(rect.getAttribute("width")) * Number(rect.getAttribute("height"))
      );
    };

    expect(area("NVDA")).toBeGreaterThan(area("V") * 3);
  });

  it("skips positions with no market value and shows the empty state", () => {
    restore = giveLayout();
    render(<Heatmap positions={[]} />);

    expect(screen.getByText("No positions yet")).toBeInTheDocument();
    expect(tiles()).toHaveLength(0);
  });
});
