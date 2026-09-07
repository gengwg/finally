const money = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const whole = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

const compact = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatMoney(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `$${money.format(value)}`;
}

/** Money with an explicit sign, for P&L figures. */
export function formatSignedMoney(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}$${money.format(Math.abs(value))}`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${Math.abs(value).toFixed(2)}%`;
}

export function formatPrice(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return money.format(value);
}

export function formatQuantity(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(4);
}

export function formatCompactMoney(value: number): string {
  return `$${compact.format(value)}`;
}

/**
 * Tick formatter for a money axis. A compact label collapses to the same
 * string on every tick when the axis spans only a few dollars — a portfolio
 * sitting at $10,000.38 would show "$10K" five times — so the precision
 * widens as the span narrows.
 */
export function moneyAxisFormatter(span: number): (value: number) => string {
  if (span >= 10_000) return formatCompactMoney;
  if (span >= 10) return (value) => `$${whole.format(value)}`;
  return (value) => `$${money.format(value)}`;
}

export function formatClock(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

/** Tailwind text colour for a signed figure. */
export function toneClass(value: number | null | undefined): string {
  if (value == null || value === 0) return "text-ink-muted";
  return value > 0 ? "text-up" : "text-down";
}
