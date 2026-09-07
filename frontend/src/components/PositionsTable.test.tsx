import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PositionsTable } from "./PositionsTable";
import { portfolio, priceMap } from "@/test/fixtures";

describe("PositionsTable", () => {
  it("renders a row per position from the portfolio payload", () => {
    render(
      <PositionsTable
        positions={portfolio.positions}
        prices={{}}
        selected={null}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByTestId("positions-table")).toBeInTheDocument();
    const row = within(screen.getByTestId("position-row-AAPL"));
    expect(row.getByText("10")).toBeInTheDocument();
    expect(row.getByText("192.00")).toBeInTheDocument();
    expect(row.getByText("193.50")).toBeInTheDocument();
    expect(row.getByText("$1,935.00")).toBeInTheDocument();
    expect(row.getByText("+$15.00")).toBeInTheDocument();
    expect(row.getByText("+0.78%")).toBeInTheDocument();
  });

  it("shows a loss as a negative P&L", () => {
    render(
      <PositionsTable
        positions={portfolio.positions}
        prices={{}}
        selected={null}
        onSelect={vi.fn()}
      />,
    );

    const row = within(screen.getByTestId("position-row-TSLA"));
    expect(row.getByText("-$40.00")).toBeInTheDocument();
    expect(row.getByText("-4.00%")).toBeInTheDocument();
  });

  it("revalues positions from the live price stream", () => {
    render(
      <PositionsTable
        positions={portfolio.positions}
        prices={priceMap({ AAPL: 202 })}
        selected={null}
        onSelect={vi.fn()}
      />,
    );

    const row = within(screen.getByTestId("position-row-AAPL"));
    expect(row.getByText("202.00")).toBeInTheDocument();
    expect(row.getByText("$2,020.00")).toBeInTheDocument();
    expect(row.getByText("+$100.00")).toBeInTheDocument();
  });

  it("selects a ticker when its row is clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <PositionsTable
        positions={portfolio.positions}
        prices={{}}
        selected={null}
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByTestId("position-row-TSLA"));
    expect(onSelect).toHaveBeenCalledWith("TSLA");
  });

  it("explains the empty state instead of rendering a table", () => {
    render(
      <PositionsTable
        positions={[]}
        prices={{}}
        selected={null}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("positions-table")).not.toBeInTheDocument();
    expect(screen.getByText(/No open positions/)).toBeInTheDocument();
  });
});
