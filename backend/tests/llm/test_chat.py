"""The chat flow: prompt construction, action execution, persistence."""

import pytest

from app.db import get_cash_balance, get_position, list_chat_messages, list_watchlist
from app.llm.chat import handle_message
from app.llm.client import LLMError

BUY_10_AAPL = [{"ticker": "AAPL", "side": "buy", "quantity": 10}]


def tickers():
    return [entry.ticker for entry in list_watchlist()]


class TestPromptConstruction:
    """What the model is actually shown."""

    def test_system_prompt_first(self, cache, model):
        handle_message(cache, "how am I doing?")

        assert model.messages[0]["role"] == "system"
        assert "FinAlly" in model.messages[0]["content"]

    def test_portfolio_context_included(self, cache, model):
        handle_message(cache, "how am I doing?")

        context = model.messages[1]["content"]
        assert "Cash balance: $10,000.00" in context
        assert "Total value: $10,000.00" in context
        assert "AAPL: $190.00" in context

    def test_context_reflects_current_positions(self, cache, model):
        model.set(trades=BUY_10_AAPL)
        handle_message(cache, "buy")

        handle_message(cache, "how am I doing?")
        context = model.messages[1]["content"]
        assert "AAPL: 10 shares, avg cost $190.00" in context
        assert "Cash balance: $8,100.00" in context

    def test_user_message_is_last(self, cache, model):
        handle_message(cache, "what should I do?")

        assert model.messages[-1] == {"role": "user", "content": "what should I do?"}

    def test_history_replayed_between_context_and_new_message(self, cache, model):
        model.set(message="Looking flat.")
        handle_message(cache, "first question")

        handle_message(cache, "second question")
        replayed = [(m["role"], m["content"]) for m in model.messages[2:]]
        assert replayed == [
            ("user", "first question"),
            ("assistant", "Looking flat."),
            ("user", "second question"),
        ]


class TestTradeExecution:
    """Trades from the model go through the same validation as manual ones."""

    def test_successful_buy(self, cache, model):
        model.set(message="Bought 10 AAPL.", trades=BUY_10_AAPL)

        body = handle_message(cache, "buy 10 AAPL")

        assert body["message"] == "Bought 10 AAPL."
        assert body["trades"] == [
            {
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10.0,
                "status": "executed",
                "price": 190.0,
                "error": None,
            }
        ]
        assert get_position("AAPL").quantity == 10.0
        assert get_cash_balance() == 8100.0

    def test_portfolio_reflects_the_executed_trade(self, cache, model):
        model.set(trades=BUY_10_AAPL)

        portfolio = handle_message(cache, "buy")["portfolio"]

        assert portfolio["cash_balance"] == 8100.0
        assert portfolio["total_value"] == 10000.0
        assert [p["ticker"] for p in portfolio["positions"]] == ["AAPL"]

    def test_successful_sell(self, cache, model):
        model.set(trades=BUY_10_AAPL)
        handle_message(cache, "buy")
        model.set(trades=[{"ticker": "AAPL", "side": "sell", "quantity": 4}])

        body = handle_message(cache, "sell 4")

        assert body["trades"][0]["status"] == "executed"
        assert get_position("AAPL").quantity == 6.0
        assert get_cash_balance() == pytest.approx(8860.0)

    def test_insufficient_cash_fails_with_200_worth_of_detail(self, cache, model):
        model.set(message="Trying.", trades=[{"ticker": "AAPL", "side": "buy", "quantity": 1000}])

        body = handle_message(cache, "buy 1000 AAPL")

        trade = body["trades"][0]
        assert trade["status"] == "failed"
        assert trade["price"] is None
        assert "Insufficient cash" in trade["error"]
        assert get_position("AAPL") is None
        assert get_cash_balance() == 10000.0
        assert body["message"] == "Trying."

    def test_insufficient_shares_fails(self, cache, model):
        model.set(trades=[{"ticker": "MSFT", "side": "sell", "quantity": 3}])

        trade = handle_message(cache, "sell MSFT")["trades"][0]

        assert trade["status"] == "failed"
        assert "Insufficient shares" in trade["error"]

    def test_unpriced_ticker_fails(self, cache, model):
        model.set(trades=[{"ticker": "PYPL", "side": "buy", "quantity": 1}])

        trade = handle_message(cache, "buy PYPL")["trades"][0]

        assert trade["status"] == "failed"
        assert "No price available for PYPL" in trade["error"]

    def test_one_failure_does_not_stop_the_others(self, cache, model):
        model.set(
            trades=[
                {"ticker": "AAPL", "side": "buy", "quantity": 5},
                {"ticker": "MSFT", "side": "buy", "quantity": 500},
                {"ticker": "NVDA", "side": "buy", "quantity": 2},
            ]
        )

        trades = handle_message(cache, "rebalance")["trades"]

        assert [t["status"] for t in trades] == ["executed", "failed", "executed"]
        assert get_position("AAPL").quantity == 5.0
        assert get_position("MSFT") is None
        assert get_position("NVDA").quantity == 2.0

    def test_lowercase_ticker_from_the_model_is_normalised(self, cache, model):
        model.set(trades=[{"ticker": "aapl", "side": "buy", "quantity": 1}])

        trade = handle_message(cache, "buy apple")["trades"][0]

        assert trade["ticker"] == "AAPL"
        assert trade["status"] == "executed"


class TestWatchlistChanges:
    """Watchlist edits are reported per action, same as trades."""

    def test_add_new_ticker(self, cache, model):
        model.set(message="Watching PYPL.", watchlist_changes=[{"ticker": "PYPL", "action": "add"}])

        body = handle_message(cache, "watch PYPL")

        assert body["watchlist_changes"] == [
            {"ticker": "PYPL", "action": "add", "status": "executed", "error": None}
        ]
        assert "PYPL" in tickers()

    def test_add_existing_ticker_fails(self, cache, model):
        model.set(watchlist_changes=[{"ticker": "AAPL", "action": "add"}])

        change = handle_message(cache, "watch AAPL")["watchlist_changes"][0]

        assert change["status"] == "failed"
        assert "already on the watchlist" in change["error"]

    def test_remove_ticker(self, cache, model):
        model.set(watchlist_changes=[{"ticker": "AAPL", "action": "remove"}])

        change = handle_message(cache, "drop AAPL")["watchlist_changes"][0]

        assert change["status"] == "executed"
        assert "AAPL" not in tickers()

    def test_remove_absent_ticker_fails(self, cache, model):
        model.set(watchlist_changes=[{"ticker": "PYPL", "action": "remove"}])

        change = handle_message(cache, "drop PYPL")["watchlist_changes"][0]

        assert change["status"] == "failed"
        assert "not on the watchlist" in change["error"]

    def test_mixed_batch_of_trades_and_watchlist_changes(self, cache, model):
        model.set(
            message="Done.",
            trades=BUY_10_AAPL,
            watchlist_changes=[
                {"ticker": "PYPL", "action": "add"},
                {"ticker": "AAPL", "action": "add"},
                {"ticker": "MSFT", "action": "remove"},
            ],
        )

        body = handle_message(cache, "do it all")

        assert body["trades"][0]["status"] == "executed"
        assert [c["status"] for c in body["watchlist_changes"]] == [
            "executed",
            "failed",
            "executed",
        ]

    def test_a_buy_puts_the_ticker_on_the_watchlist(self, cache, model):
        model.set(watchlist_changes=[{"ticker": "AAPL", "action": "remove"}])
        handle_message(cache, "drop AAPL")
        model.set(trades=BUY_10_AAPL)

        handle_message(cache, "buy AAPL")

        assert "AAPL" in tickers()


class TestAnalysisOnly:
    """A reply with no actions."""

    def test_no_actions(self, cache, model):
        model.set(message="You are well diversified.")

        body = handle_message(cache, "how am I doing?")

        assert body["message"] == "You are well diversified."
        assert body["trades"] == []
        assert body["watchlist_changes"] == []
        assert body["portfolio"]["cash_balance"] == 10000.0

    def test_response_keys(self, cache, model):
        body = handle_message(cache, "hello")

        assert set(body) == {"message", "trades", "watchlist_changes", "portfolio"}


class TestPersistence:
    """Both sides of the turn are written, with the executed actions attached."""

    def test_user_then_assistant(self, cache, model):
        model.set(message="Noted.")

        handle_message(cache, "hello there")

        stored = list_chat_messages()
        assert [(m.role, m.content) for m in stored] == [
            ("user", "hello there"),
            ("assistant", "Noted."),
        ]

    def test_user_message_has_no_actions(self, cache, model):
        handle_message(cache, "hello")

        assert list_chat_messages()[0].actions is None

    def test_actions_json_round_trips(self, cache, model):
        model.set(
            message="Bought.",
            trades=BUY_10_AAPL,
            watchlist_changes=[{"ticker": "PYPL", "action": "add"}],
        )

        body = handle_message(cache, "buy 10 AAPL and watch PYPL")

        actions = list_chat_messages()[1].actions
        assert actions == {
            "trades": body["trades"],
            "watchlist_changes": body["watchlist_changes"],
        }

    def test_failed_actions_are_persisted_too(self, cache, model):
        model.set(trades=[{"ticker": "AAPL", "side": "buy", "quantity": 1000}])

        handle_message(cache, "buy 1000 AAPL")

        trade = list_chat_messages()[1].actions["trades"][0]
        assert trade["status"] == "failed"
        assert "Insufficient cash" in trade["error"]

    def test_empty_action_lists_are_stored_not_null(self, cache, model):
        handle_message(cache, "hello")

        assert list_chat_messages()[1].actions == {"trades": [], "watchlist_changes": []}

    def test_history_is_chronological_across_turns(self, cache, model):
        handle_message(cache, "one")
        handle_message(cache, "two")

        assert [m.content for m in list_chat_messages()] == ["one", "ok", "two", "ok"]


class TestModelFailure:
    """Nothing is persisted or executed when the call itself fails."""

    def test_llm_error_propagates(self, cache, model):
        model.fail(ConnectionError("openrouter unreachable"))

        with pytest.raises(LLMError):
            handle_message(cache, "buy 10 AAPL")

    def test_nothing_persisted_on_failure(self, cache, model):
        model.fail(ConnectionError("down"))

        with pytest.raises(LLMError):
            handle_message(cache, "buy 10 AAPL")

        assert list_chat_messages() == []
        assert get_cash_balance() == 10000.0

    def test_unparseable_reply_raises(self, cache, model):
        model.raw("I bought it for you!")

        with pytest.raises(LLMError):
            handle_message(cache, "buy 10 AAPL")

        assert get_position("AAPL") is None


class TestMockMode:
    """LLM_MOCK routes the whole flow through the deterministic replies."""

    def test_mock_buy_executes(self, cache, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")

        body = handle_message(cache, "buy 10 AAPL")

        assert body["message"] == "Buying 10 AAPL at market."
        assert body["trades"][0]["status"] == "executed"
        assert body["portfolio"]["cash_balance"] == 8100.0

    def test_mock_analysis_has_no_actions(self, cache, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")

        body = handle_message(cache, "how am I doing?")

        assert body["trades"] == []
        assert body["watchlist_changes"] == []
