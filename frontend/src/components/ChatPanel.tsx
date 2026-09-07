"use client";

import { useEffect, useRef, useState } from "react";
import { formatPrice, formatQuantity } from "@/lib/format";
import type { ChatActions, ChatMessage } from "@/lib/types";

function Chip({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <span
      className={`num inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] ${
        ok
          ? "border-up/40 bg-up/10 text-up"
          : "border-down/40 bg-down/10 text-down"
      }`}
    >
      {children}
    </span>
  );
}

function Actions({ actions }: { actions: ChatActions }) {
  const trades = actions.trades ?? [];
  const changes = actions.watchlist_changes ?? [];
  if (trades.length === 0 && changes.length === 0) return null;

  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5">
      {trades.map((trade, index) => (
        <Chip key={`t${index}`} ok={trade.status === "executed"}>
          {trade.side.toUpperCase()} {formatQuantity(trade.quantity)}{" "}
          {trade.ticker}
          {trade.price != null && ` @ ${formatPrice(trade.price)}`}
          {trade.error && ` — ${trade.error}`}
        </Chip>
      ))}
      {changes.map((change, index) => (
        <Chip key={`w${index}`} ok={change.status === "executed"}>
          {change.action.toUpperCase()} {change.ticker}
          {change.error && ` — ${change.error}`}
        </Chip>
      ))}
    </div>
  );
}

interface ChatPanelProps {
  messages: ChatMessage[];
  busy: boolean;
  error: string | null;
  onSend: (message: string) => void;
}

export function ChatPanel({ messages, busy, error, onSend }: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const [open, setOpen] = useState(true);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, busy]);

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open AI assistant"
        className="flex w-9 shrink-0 flex-col items-center gap-2 rounded border border-line bg-panel py-3 text-[10px] tracking-[0.14em] text-ink-muted uppercase hover:text-ink"
      >
        <span className="h-2 w-2 rounded-full bg-accent" />
        <span className="[writing-mode:vertical-rl]">FinAlly AI</span>
      </button>
    );
  }

  return (
    <section
      data-testid="chat-panel"
      className="flex w-[22rem] shrink-0 flex-col overflow-hidden rounded border border-line bg-panel"
    >
      <header className="flex h-8 shrink-0 items-center justify-between border-b border-line bg-panel-head px-2.5">
        <h2 className="text-[10px] font-semibold tracking-[0.14em] text-ink-muted uppercase">
          FinAlly assistant
        </h2>
        <button
          type="button"
          onClick={() => setOpen(false)}
          aria-label="Collapse AI assistant"
          className="text-ink-dim hover:text-ink"
        >
          ›
        </button>
      </header>

      <div className="scroll-thin min-h-0 flex-1 space-y-2.5 overflow-y-auto p-2.5">
        {messages.length === 0 && (
          <p className="text-xs leading-relaxed text-ink-dim">
            Ask about your portfolio, request analysis, or say
            &ldquo;buy 10 NVDA&rdquo; and FinAlly will place the trade.
          </p>
        )}
        {messages.map((message, index) => (
          <div
            key={index}
            data-testid={`chat-message-${index}`}
            data-role={message.role}
            className={message.role === "user" ? "pl-6" : ""}
          >
            <div
              className={`rounded border px-2.5 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
                message.role === "user"
                  ? "border-brand/30 bg-brand/10"
                  : "border-line bg-panel-head"
              }`}
            >
              {message.content}
              {message.role === "assistant" && message.actions && (
                <Actions actions={message.actions} />
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div
            data-testid="chat-loading"
            className="flex items-center gap-1.5 px-1 text-[10px] tracking-[0.14em] text-ink-muted uppercase"
          >
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
            Thinking
          </div>
        )}
        {error && <p className="px-1 text-xs text-down">{error}</p>}
        <div ref={endRef} />
      </div>

      <form
        className="shrink-0 border-t border-line bg-panel-head p-2"
        onSubmit={(event) => {
          event.preventDefault();
          const message = draft.trim();
          if (!message || busy) return;
          onSend(message);
          setDraft("");
        }}
      >
        <div className="flex gap-1.5">
          <input
            data-testid="chat-input"
            aria-label="Message FinAlly"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ask FinAlly…"
            className="min-w-0 flex-1 rounded border border-line bg-ground px-2 py-1.5 text-xs placeholder:text-ink-dim focus:border-brand focus:outline-none"
          />
          <button
            type="submit"
            data-testid="chat-send"
            disabled={busy}
            className="rounded bg-submit px-3 py-1.5 text-xs font-semibold text-ink hover:brightness-125 disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </form>
    </section>
  );
}
