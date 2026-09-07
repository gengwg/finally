"""Portfolio valuation and trade execution."""

from __future__ import annotations

from dataclasses import dataclass

from app.db import (
    DEFAULT_USER_ID,
    Position,
    Snapshot,
    Trade,
    add_to_watchlist,
    delete_position,
    get_cash_balance,
    get_connection,
    get_position,
    list_positions,
    record_snapshot,
    record_trade,
    set_cash_balance,
    upsert_position,
)
from app.market import PriceCache

# A sell leaving less than this many shares closes the position outright, so
# float arithmetic cannot leave a dust row behind.
DUST_QUANTITY = 1e-9


class TradeError(Exception):
    """Validation failure — insufficient cash, insufficient shares, unknown ticker."""


@dataclass(frozen=True, slots=True)
class PositionView:
    """A position valued at the current market price."""

    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    pnl_percent: float

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "quantity": self.quantity,
            "avg_cost": round(self.avg_cost, 2),
            "current_price": round(self.current_price, 2),
            "market_value": round(self.market_value, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "pnl_percent": round(self.pnl_percent, 2),
        }


@dataclass(frozen=True, slots=True)
class PortfolioView:
    """Cash, positions and the totals derived from them."""

    cash_balance: float
    positions: list[PositionView]
    positions_value: float
    total_value: float
    total_unrealized_pnl: float

    def to_dict(self) -> dict:
        return {
            "cash_balance": round(self.cash_balance, 2),
            "positions": [position.to_dict() for position in self.positions],
            "positions_value": round(self.positions_value, 2),
            "total_value": round(self.total_value, 2),
            "total_unrealized_pnl": round(self.total_unrealized_pnl, 2),
        }


def get_portfolio(cache: PriceCache, *, user_id: str = DEFAULT_USER_ID) -> PortfolioView:
    """Value every open position against the price cache and total it up with cash."""
    positions = [_value_position(position, cache) for position in list_positions(user_id=user_id)]
    cash_balance = get_cash_balance(user_id=user_id)
    positions_value = sum(position.market_value for position in positions)

    return PortfolioView(
        cash_balance=cash_balance,
        positions=positions,
        positions_value=positions_value,
        total_value=cash_balance + positions_value,
        total_unrealized_pnl=sum(position.unrealized_pnl for position in positions),
    )


def execute_trade(
    cache: PriceCache,
    ticker: str,
    side: str,
    quantity: float,
    *,
    user_id: str = DEFAULT_USER_ID,
) -> tuple[Trade, PortfolioView]:
    """Fill a market order at the cached price. Raises TradeError on any validation failure."""
    ticker = ticker.strip().upper()
    side = side.strip().lower()

    if side not in ("buy", "sell"):
        raise TradeError(f"Invalid side '{side}': must be 'buy' or 'sell'")
    if quantity <= 0:
        raise TradeError("Quantity must be greater than zero")

    price = cache.get_price(ticker)
    if price is None:
        raise TradeError(f"No price available for {ticker}")

    cash_balance = get_cash_balance(user_id=user_id)
    position = get_position(ticker, user_id=user_id)

    if side == "buy":
        cost = price * quantity
        if cost > cash_balance:
            raise TradeError(
                f"Insufficient cash: {quantity:g} {ticker} costs ${cost:,.2f}, "
                f"cash balance is ${cash_balance:,.2f}"
            )
        cash_balance -= cost
        held = position.quantity if position else 0.0
        remaining = held + quantity
        avg_cost = (
            ((position.avg_cost * held) + (price * quantity)) / remaining if position else price
        )
    else:
        held = position.quantity if position else 0.0
        if quantity > held:
            raise TradeError(
                f"Insufficient shares: holding {held:g} {ticker}, tried to sell {quantity:g}"
            )
        cash_balance += price * quantity
        remaining = held - quantity
        avg_cost = position.avg_cost if position else 0.0

    with get_connection() as conn:
        set_cash_balance(cash_balance, user_id=user_id, conn=conn)
        if remaining <= DUST_QUANTITY:
            delete_position(ticker, user_id=user_id, conn=conn)
        else:
            upsert_position(ticker, remaining, avg_cost, user_id=user_id, conn=conn)
        if side == "buy":
            # Own it, watch it — otherwise the position has no visible price feed.
            add_to_watchlist(ticker, user_id=user_id, conn=conn)
        trade = record_trade(ticker, side, quantity, price, user_id=user_id, conn=conn)
        conn.commit()

    record_current_snapshot(cache, user_id=user_id)
    return trade, get_portfolio(cache, user_id=user_id)


def record_current_snapshot(cache: PriceCache, *, user_id: str = DEFAULT_USER_ID) -> Snapshot:
    """Append the current total portfolio value to the snapshot history."""
    portfolio = get_portfolio(cache, user_id=user_id)
    return record_snapshot(portfolio.total_value, user_id=user_id)


def _value_position(position: Position, cache: PriceCache) -> PositionView:
    price = cache.get_price(position.ticker)
    # No cached price yet (ticker added seconds ago): value at cost so the
    # position shows with zero P&L rather than collapsing to zero.
    current_price = position.avg_cost if price is None else price

    return PositionView(
        ticker=position.ticker,
        quantity=position.quantity,
        avg_cost=position.avg_cost,
        current_price=current_price,
        market_value=current_price * position.quantity,
        unrealized_pnl=(current_price - position.avg_cost) * position.quantity,
        pnl_percent=(
            0.0 if position.avg_cost == 0 else (current_price / position.avg_cost - 1) * 100
        ),
    )
