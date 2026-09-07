import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TradeBar } from "./TradeBar";

const props = {
  ticker: "AAPL",
  onTickerChange: vi.fn(),
  price: 193.5,
  busy: false,
  error: null,
  onTrade: vi.fn(),
};

describe("TradeBar", () => {
  it("submits a buy and a sell for the entered quantity", async () => {
    const onTrade = vi.fn();
    const user = userEvent.setup();
    render(<TradeBar {...props} onTrade={onTrade} />);

    const quantity = screen.getByTestId("trade-quantity");
    await user.clear(quantity);
    await user.type(quantity, "2.5");
    await user.click(screen.getByTestId("trade-buy"));
    await user.click(screen.getByTestId("trade-sell"));

    expect(onTrade).toHaveBeenNthCalledWith(1, "AAPL", 2.5, "buy");
    expect(onTrade).toHaveBeenNthCalledWith(2, "AAPL", 2.5, "sell");
  });

  it("shows the estimated notional for the order", () => {
    render(<TradeBar {...props} onTrade={vi.fn()} />);
    expect(screen.getByText("≈ $193.50")).toBeInTheDocument();
  });

  it("refuses a non-positive quantity", async () => {
    const onTrade = vi.fn();
    const user = userEvent.setup();
    render(<TradeBar {...props} onTrade={onTrade} />);

    const quantity = screen.getByTestId("trade-quantity");
    await user.clear(quantity);
    await user.type(quantity, "0");

    expect(screen.getByTestId("trade-buy")).toBeDisabled();
    await user.click(screen.getByTestId("trade-buy"));
    expect(onTrade).not.toHaveBeenCalled();
  });

  it("renders the rejection message only when a trade fails", () => {
    const { rerender } = render(<TradeBar {...props} onTrade={vi.fn()} />);
    expect(screen.queryByTestId("trade-error")).not.toBeInTheDocument();

    rerender(
      <TradeBar {...props} onTrade={vi.fn()} error="Insufficient cash" />,
    );
    expect(screen.getByTestId("trade-error")).toHaveTextContent(
      "Insufficient cash",
    );
  });

  it("upper-cases ticker input", async () => {
    const onTickerChange = vi.fn();
    const user = userEvent.setup();
    render(
      <TradeBar {...props} ticker="" onTickerChange={onTickerChange} onTrade={vi.fn()} />,
    );

    await user.type(screen.getByTestId("trade-ticker"), "n");
    expect(onTickerChange).toHaveBeenCalledWith("N");
  });
});
