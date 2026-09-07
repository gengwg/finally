"""Portfolio valuation and trade execution."""

import pytest

from app.db import (
    get_cash_balance,
    get_position,
    list_snapshots,
    list_trades,
    list_watchlist,
    upsert_position,
)
from app.services.portfolio import (
    TradeError,
    execute_trade,
    get_portfolio,
    record_current_snapshot,
)


class TestGetPortfolio:
    def test_fresh_account_is_all_cash(self, cache):
        portfolio = get_portfolio(cache)

        assert portfolio.cash_balance == 10000.0
        assert portfolio.positions == []
        assert portfolio.positions_value == 0.0
        assert portfolio.total_value == 10000.0
        assert portfolio.total_unrealized_pnl == 0.0

    def test_values_a_profit_and_a_loss_position(self, cache):
        execute_trade(cache, "AAPL", "buy", 10)
        execute_trade(cache, "MSFT", "buy", 2)
        cache.update("AAPL", 200.0)
        cache.update("MSFT", 380.0)

        portfolio = get_portfolio(cache)
        aapl, msft = portfolio.positions

        assert aapl.ticker == "AAPL"
        assert aapl.market_value == 2000.0
        assert aapl.unrealized_pnl == 100.0
        assert aapl.pnl_percent == pytest.approx(5.2631, abs=1e-4)

        assert msft.ticker == "MSFT"
        assert msft.market_value == 760.0
        assert msft.unrealized_pnl == -40.0
        assert msft.pnl_percent == pytest.approx(-5.0)

        # 10000 - 1900 - 800 = 7300 cash
        assert portfolio.cash_balance == 7300.0
        assert portfolio.positions_value == 2760.0
        assert portfolio.total_value == 10060.0
        assert portfolio.total_unrealized_pnl == 60.0

    def test_position_without_a_cached_price_is_valued_at_cost(self, cache):
        upsert_position("PYPL", 5, 60.0)

        position = get_portfolio(cache).positions[0]

        assert position.current_price == 60.0
        assert position.market_value == 300.0
        assert position.unrealized_pnl == 0.0
        assert position.pnl_percent == 0.0

    def test_zero_avg_cost_gives_zero_percent(self, cache):
        upsert_position("AAPL", 4, 0.0)

        position = get_portfolio(cache).positions[0]

        assert position.unrealized_pnl == 760.0
        assert position.pnl_percent == 0.0

    def test_to_dict_rounds_money_and_percentages(self, cache):
        execute_trade(cache, "AAPL", "buy", 3)
        cache.update("AAPL", 193.333)

        body = get_portfolio(cache).to_dict()

        assert body["positions"][0] == {
            "ticker": "AAPL",
            "quantity": 3.0,
            "avg_cost": 190.0,
            "current_price": 193.33,
            "market_value": 579.99,
            "unrealized_pnl": 9.99,
            "pnl_percent": 1.75,
        }
        assert body["cash_balance"] == 9430.0
        assert body["total_value"] == 10009.99


class TestExecuteTrade:
    def test_buy_moves_cash_position_and_trade_log(self, cache):
        trade, portfolio = execute_trade(cache, "AAPL", "buy", 10)

        assert trade.ticker == "AAPL"
        assert trade.side == "buy"
        assert trade.quantity == 10.0
        assert trade.price == 190.0
        assert get_cash_balance() == 8100.0
        assert get_position("AAPL").quantity == 10.0
        assert portfolio.cash_balance == 8100.0
        assert [t.id for t in list_trades()] == [trade.id]

    def test_buy_then_sell_round_trip(self, cache):
        execute_trade(cache, "AAPL", "buy", 10)
        cache.update("AAPL", 200.0)
        trade, portfolio = execute_trade(cache, "AAPL", "sell", 4)

        assert trade.side == "sell"
        assert trade.price == 200.0
        position = get_position("AAPL")
        assert position.quantity == 6.0
        assert position.avg_cost == 190.0  # unchanged by a sell
        assert portfolio.cash_balance == pytest.approx(8900.0)  # 8100 + 4 * 200
        assert [t.side for t in list_trades()] == ["sell", "buy"]

    def test_avg_cost_is_weighted_across_two_buys(self, cache):
        execute_trade(cache, "AAPL", "buy", 10)
        cache.update("AAPL", 210.0)
        execute_trade(cache, "AAPL", "buy", 30)

        position = get_position("AAPL")
        assert position.quantity == 40.0
        # (10 * 190 + 30 * 210) / 40
        assert position.avg_cost == pytest.approx(205.0)

    def test_full_liquidation_removes_the_position(self, cache):
        execute_trade(cache, "AAPL", "buy", 7.5)
        execute_trade(cache, "AAPL", "sell", 7.5)

        assert get_position("AAPL") is None
        assert get_cash_balance() == pytest.approx(10000.0)

    def test_float_dust_still_closes_the_position(self, cache):
        execute_trade(cache, "AAPL", "buy", 0.1)
        execute_trade(cache, "AAPL", "buy", 0.2)
        execute_trade(cache, "AAPL", "sell", 0.3)

        assert get_position("AAPL") is None

    def test_fractional_shares(self, cache):
        trade, _ = execute_trade(cache, "AAPL", "buy", 0.5)

        assert trade.quantity == 0.5
        assert get_cash_balance() == 9905.0

    def test_ticker_and_side_are_normalised(self, cache):
        trade, _ = execute_trade(cache, " aapl ", "BUY", 1)

        assert trade.ticker == "AAPL"
        assert trade.side == "buy"

    def test_buy_adds_the_ticker_to_the_watchlist(self, cache):
        cache.update("PYPL", 60.0)
        execute_trade(cache, "PYPL", "buy", 1)

        assert "PYPL" in [entry.ticker for entry in list_watchlist()]

    def test_buy_of_a_watched_ticker_does_not_duplicate_it(self, cache):
        execute_trade(cache, "AAPL", "buy", 1)

        assert [entry.ticker for entry in list_watchlist()].count("AAPL") == 1

    def test_trade_records_a_snapshot(self, cache):
        execute_trade(cache, "AAPL", "buy", 10)

        snapshots = list_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0].total_value == pytest.approx(10000.0)


class TestTradeValidation:
    def test_insufficient_cash(self, cache):
        with pytest.raises(TradeError, match="Insufficient cash"):
            execute_trade(cache, "AAPL", "buy", 100)

        assert get_cash_balance() == 10000.0
        assert get_position("AAPL") is None
        assert list_trades() == []

    def test_buy_spending_exactly_the_cash_balance_is_allowed(self, cache):
        cache.update("AAPL", 100.0)
        execute_trade(cache, "AAPL", "buy", 100)

        assert get_cash_balance() == 0.0

    def test_insufficient_shares(self, cache):
        execute_trade(cache, "AAPL", "buy", 2)

        with pytest.raises(TradeError, match="Insufficient shares"):
            execute_trade(cache, "AAPL", "sell", 3)

        assert get_position("AAPL").quantity == 2.0

    def test_sell_without_a_position(self, cache):
        with pytest.raises(TradeError, match="Insufficient shares"):
            execute_trade(cache, "AAPL", "sell", 1)

    @pytest.mark.parametrize("quantity", [0, -5, -0.001])
    def test_non_positive_quantity(self, cache, quantity):
        with pytest.raises(TradeError, match="greater than zero"):
            execute_trade(cache, "AAPL", "buy", quantity)

    @pytest.mark.parametrize("side", ["hold", "", "b uy"])
    def test_bad_side(self, cache, side):
        with pytest.raises(TradeError, match="Invalid side"):
            execute_trade(cache, "AAPL", side, 1)

    def test_unknown_ticker(self, cache):
        with pytest.raises(TradeError, match="No price available for ZZZZ"):
            execute_trade(cache, "ZZZZ", "buy", 1)

    def test_failed_trade_records_no_snapshot(self, cache):
        with pytest.raises(TradeError):
            execute_trade(cache, "AAPL", "buy", 1000)

        assert list_snapshots() == []


class TestRecordCurrentSnapshot:
    def test_snapshot_captures_total_value(self, cache):
        execute_trade(cache, "AAPL", "buy", 10)
        cache.update("AAPL", 200.0)

        snapshot = record_current_snapshot(cache)

        assert snapshot.total_value == pytest.approx(10100.0)
        assert [s.total_value for s in list_snapshots()][-1] == pytest.approx(10100.0)
