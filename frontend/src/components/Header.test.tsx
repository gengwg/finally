import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Header } from "./Header";

const base = {
  totalValue: 10975,
  cashBalance: 8080,
  unrealizedPnl: -25,
  status: "connected" as const,
};

describe("Header", () => {
  it("shows the portfolio total, cash and P&L", () => {
    render(<Header {...base} />);
    expect(screen.getByTestId("total-value")).toHaveTextContent("$10,975.00");
    expect(screen.getByTestId("cash-balance")).toHaveTextContent("$8,080.00");
    expect(screen.getByText("-$25.00")).toBeInTheDocument();
  });

  it("exposes the stream state on the status dot", () => {
    const { rerender } = render(<Header {...base} />);
    const dot = () => screen.getByTestId("connection-status");
    expect(dot()).toHaveAttribute("data-state", "connected");

    rerender(<Header {...base} status="reconnecting" />);
    expect(dot()).toHaveAttribute("data-state", "reconnecting");

    rerender(<Header {...base} status="disconnected" />);
    expect(dot()).toHaveAttribute("data-state", "disconnected");
  });
});
