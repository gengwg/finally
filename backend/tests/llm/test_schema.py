"""Tests for the structured-output schema."""

import pytest
from pydantic import ValidationError

from app.llm.schema import AssistantReply, TradeInstruction, WatchlistChange


class TestTradeInstruction:
    """Validation and normalisation of a single trade."""

    def test_ticker_upper_cased(self):
        trade = TradeInstruction(ticker="aapl", side="buy", quantity=10)
        assert trade.ticker == "AAPL"

    def test_ticker_whitespace_stripped(self):
        trade = TradeInstruction(ticker="  tsla ", side="sell", quantity=1)
        assert trade.ticker == "TSLA"

    def test_quantity_coerced_to_float(self):
        trade = TradeInstruction(ticker="AAPL", side="buy", quantity=10)
        assert trade.quantity == 10.0
        assert isinstance(trade.quantity, float)

    def test_fractional_quantity(self):
        assert TradeInstruction(ticker="AAPL", side="buy", quantity=0.5).quantity == 0.5

    def test_invalid_side_rejected(self):
        with pytest.raises(ValidationError):
            TradeInstruction(ticker="AAPL", side="hold", quantity=1)

    def test_missing_quantity_rejected(self):
        with pytest.raises(ValidationError):
            TradeInstruction(ticker="AAPL", side="buy")


class TestWatchlistChange:
    """Validation and normalisation of a watchlist edit."""

    def test_ticker_upper_cased(self):
        assert WatchlistChange(ticker="pypl", action="add").ticker == "PYPL"

    def test_both_actions_allowed(self):
        assert WatchlistChange(ticker="V", action="remove").action == "remove"
        assert WatchlistChange(ticker="V", action="add").action == "add"

    def test_invalid_action_rejected(self):
        with pytest.raises(ValidationError):
            WatchlistChange(ticker="V", action="delete")


class TestAssistantReply:
    """The top-level reply model."""

    def test_actions_default_to_empty(self):
        reply = AssistantReply(message="hello")
        assert reply.trades == []
        assert reply.watchlist_changes == []

    def test_defaults_are_not_shared_between_instances(self):
        first = AssistantReply(message="a")
        first.trades.append(TradeInstruction(ticker="AAPL", side="buy", quantity=1))
        assert AssistantReply(message="b").trades == []

    def test_message_is_required(self):
        with pytest.raises(ValidationError):
            AssistantReply(trades=[])

    def test_parsed_from_json(self):
        raw = """
        {"message": "Bought it.",
         "trades": [{"ticker": "aapl", "side": "buy", "quantity": 10}],
         "watchlist_changes": [{"ticker": "pypl", "action": "add"}]}
        """
        reply = AssistantReply.model_validate_json(raw)
        assert reply.message == "Bought it."
        assert reply.trades[0].ticker == "AAPL"
        assert reply.watchlist_changes[0].ticker == "PYPL"

    def test_nested_validation_error_propagates(self):
        raw = '{"message": "x", "trades": [{"ticker": "AAPL", "side": "short", "quantity": 1}]}'
        with pytest.raises(ValidationError):
            AssistantReply.model_validate_json(raw)
