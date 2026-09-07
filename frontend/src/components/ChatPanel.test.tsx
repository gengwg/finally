import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatPanel } from "./ChatPanel";
import { chatHistory } from "@/test/fixtures";

const props = {
  messages: chatHistory,
  busy: false,
  error: null,
  onSend: vi.fn(),
};

describe("ChatPanel", () => {
  it("renders history in order with roles marked", () => {
    render(<ChatPanel {...props} onSend={vi.fn()} />);

    expect(screen.getByTestId("chat-message-0")).toHaveAttribute(
      "data-role",
      "user",
    );
    expect(screen.getByTestId("chat-message-0")).toHaveTextContent(
      "buy me 10 apple shares",
    );
    expect(screen.getByTestId("chat-message-1")).toHaveAttribute(
      "data-role",
      "assistant",
    );
  });

  it("renders executed trades and watchlist changes under the assistant message", () => {
    render(<ChatPanel {...props} onSend={vi.fn()} />);

    const assistant = within(screen.getByTestId("chat-message-1"));
    expect(assistant.getByText(/BUY 10 AAPL @ 192.00/)).toBeInTheDocument();
    expect(assistant.getByText(/ADD PYPL/)).toBeInTheDocument();
  });

  it("marks a failed trade and shows its error", () => {
    render(
      <ChatPanel
        {...props}
        onSend={vi.fn()}
        messages={[
          {
            role: "assistant",
            content: "I could not do that.",
            actions: {
              trades: [
                {
                  ticker: "NVDA",
                  side: "buy",
                  quantity: 100,
                  status: "failed",
                  price: null,
                  error: "Insufficient cash",
                },
              ],
            },
            created_at: "2026-09-07T12:00:00+00:00",
          },
        ]}
      />,
    );

    expect(screen.getByText(/Insufficient cash/)).toBeInTheDocument();
  });

  it("shows the loading indicator only while waiting", () => {
    const { rerender } = render(<ChatPanel {...props} onSend={vi.fn()} />);
    expect(screen.queryByTestId("chat-loading")).not.toBeInTheDocument();

    rerender(<ChatPanel {...props} onSend={vi.fn()} busy />);
    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();
  });

  it("sends a trimmed message and clears the input", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatPanel {...props} onSend={onSend} />);

    await user.type(screen.getByTestId("chat-input"), "  how am I doing?  ");
    await user.click(screen.getByTestId("chat-send"));

    expect(onSend).toHaveBeenCalledWith("how am I doing?");
    expect(screen.getByTestId("chat-input")).toHaveValue("");
  });

  it("does not send while a reply is pending", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatPanel {...props} onSend={onSend} busy messages={[]} />);

    await user.type(screen.getByTestId("chat-input"), "hello");
    await user.click(screen.getByTestId("chat-send"));

    expect(onSend).not.toHaveBeenCalled();
  });

  it("collapses and reopens the panel", async () => {
    const user = userEvent.setup();
    render(<ChatPanel {...props} onSend={vi.fn()} />);

    await user.click(screen.getByLabelText("Collapse AI assistant"));
    expect(screen.queryByTestId("chat-panel")).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("Open AI assistant"));
    expect(screen.getByTestId("chat-panel")).toBeInTheDocument();
  });

  it("shows a chat error", () => {
    render(<ChatPanel {...props} onSend={vi.fn()} error="LLM unavailable" />);
    expect(screen.getByText("LLM unavailable")).toBeInTheDocument();
  });
});
