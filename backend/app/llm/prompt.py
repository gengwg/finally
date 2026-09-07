"""System prompt and portfolio context rendering for the chat assistant."""

from __future__ import annotations

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant embedded in a simulated trading workstation.

The portfolio holds virtual money, so trades you request are executed immediately without
a confirmation step.

Your job:
- Analyse portfolio composition, concentration risk and P&L from the data you are given.
- Suggest trades with a short, concrete reason.
- Execute trades when the user asks for them or agrees to a suggestion.
- Manage the watchlist: add tickers you discuss, remove ones the user is done with.

Rules:
- Be concise and data driven. Cite the actual numbers from the portfolio context.
- Never invent prices. Use the prices in the portfolio context.
- Every trade goes in `trades` and every watchlist edit in `watchlist_changes`. Do not
  claim you did something without the matching action.
- Leave `trades` and `watchlist_changes` empty when the user only wants analysis.
- Trades are validated after you reply: a buy needs enough cash, a sell enough shares.
- Respond only with the structured object: message, trades, watchlist_changes."""


def _money(value: float) -> str:
    return f"${value:,.2f}"


def render_portfolio_context(portfolio: dict, watchlist: list[dict]) -> str:
    """Render live portfolio state as a text block for the prompt.

    `portfolio` is a `PortfolioView.to_dict()` and `watchlist` the ticker list from
    `GET /api/watchlist`. Both are taken as plain data so this module needs no
    service imports.
    """
    lines = [
        "CURRENT PORTFOLIO",
        f"Cash balance: {_money(portfolio['cash_balance'])}",
        f"Positions value: {_money(portfolio['positions_value'])}",
        f"Total value: {_money(portfolio['total_value'])}",
        f"Total unrealized P&L: {_money(portfolio['total_unrealized_pnl'])}",
        "",
        "POSITIONS",
    ]

    positions = portfolio.get("positions") or []
    if not positions:
        lines.append("(none)")
    for pos in positions:
        lines.append(
            f"{pos['ticker']}: {pos['quantity']:g} shares, avg cost {_money(pos['avg_cost'])}, "
            f"price {_money(pos['current_price'])}, value {_money(pos['market_value'])}, "
            f"P&L {_money(pos['unrealized_pnl'])} ({pos['pnl_percent']:+.2f}%)"
        )

    lines += ["", "WATCHLIST"]
    if not watchlist:
        lines.append("(empty)")
    for entry in watchlist:
        price = entry.get("price")
        if price is None:
            lines.append(f"{entry['ticker']}: no price yet")
        else:
            change = entry.get("change_percent") or 0.0
            lines.append(f"{entry['ticker']}: {_money(price)} ({change:+.2f}%)")

    return "\n".join(lines)
