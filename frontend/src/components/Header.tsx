"use client";

import type { ConnectionStatus } from "@/hooks/usePrices";
import { formatMoney, formatSignedMoney, toneClass } from "@/lib/format";

const STATUS_STYLE: Record<ConnectionStatus, { dot: string; label: string }> = {
  connected: { dot: "bg-up", label: "LIVE" },
  reconnecting: { dot: "bg-accent", label: "RECONNECTING" },
  disconnected: { dot: "bg-down", label: "OFFLINE" },
};

interface HeaderProps {
  totalValue: number;
  cashBalance: number;
  unrealizedPnl: number;
  status: ConnectionStatus;
}

function Stat({
  label,
  value,
  className = "",
  testId,
}: {
  label: string;
  value: string;
  className?: string;
  testId?: string;
}) {
  return (
    <div className="flex flex-col justify-center px-4">
      <span className="text-[9px] tracking-[0.14em] text-ink-dim uppercase">
        {label}
      </span>
      <span
        data-testid={testId}
        className={`num text-sm leading-tight ${className}`}
      >
        {value}
      </span>
    </div>
  );
}

export function Header({
  totalValue,
  cashBalance,
  unrealizedPnl,
  status,
}: HeaderProps) {
  const style = STATUS_STYLE[status];

  return (
    <header className="flex h-14 shrink-0 items-stretch justify-between border-b border-line bg-panel">
      <div className="flex items-stretch">
        <div className="flex items-center gap-2 px-4">
          <span className="h-4 w-1.5 rounded-sm bg-accent" />
          <span className="text-base font-semibold tracking-tight">
            Fin<span className="text-accent">Ally</span>
          </span>
        </div>
        <div className="w-px bg-line" />
        <Stat
          label="Total value"
          value={formatMoney(totalValue)}
          testId="total-value"
          className="text-base font-semibold"
        />
        <div className="w-px bg-line" />
        <Stat label="Cash" value={formatMoney(cashBalance)} testId="cash-balance" />
        <div className="w-px bg-line" />
        <Stat
          label="Unrealised P&L"
          value={formatSignedMoney(unrealizedPnl)}
          className={toneClass(unrealizedPnl)}
        />
      </div>

      <div
        data-testid="connection-status"
        data-state={status}
        className="flex items-center gap-2 px-4"
      >
        <span className={`h-2 w-2 rounded-full ${style.dot}`} />
        <span className="text-[10px] tracking-[0.14em] text-ink-muted uppercase">
          {style.label}
        </span>
      </div>
    </header>
  );
}
