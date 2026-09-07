"""Tests for the LLM_MOCK reply rules documented in app/llm/README.md."""

from app.llm.mock import ANALYSIS_MESSAGE, mock_complete


def user(content: str) -> list[dict]:
    return [{"role": "system", "content": "sys"}, {"role": "user", "content": content}]


class TestBuyBranch:
    """'buy' produces exactly one buy trade."""

    def test_ticker_and_quantity_parsed(self):
        reply = mock_complete(user("buy 10 AAPL"))
        assert reply.message == "Buying 10 AAPL at market."
        assert len(reply.trades) == 1
        trade = reply.trades[0]
        assert (trade.ticker, trade.side, trade.quantity) == ("AAPL", "buy", 10.0)
        assert reply.watchlist_changes == []

    def test_fractional_quantity(self):
        reply = mock_complete(user("buy 2.5 TSLA"))
        assert reply.trades[0].quantity == 2.5
        assert reply.message == "Buying 2.5 TSLA at market."

    def test_defaults_when_unspecified(self):
        reply = mock_complete(user("buy something for me"))
        assert reply.trades[0].ticker == "AAPL"
        assert reply.trades[0].quantity == 1.0

    def test_case_insensitive_keyword(self):
        assert mock_complete(user("Buy 3 NVDA")).trades[0].ticker == "NVDA"

    def test_pronoun_i_is_not_a_ticker(self):
        assert mock_complete(user("I want to buy 4 META")).trades[0].ticker == "META"

    def test_single_letter_ticker_detected(self):
        assert mock_complete(user("buy 5 V")).trades[0].ticker == "V"

    def test_lowercase_ticker_falls_back_to_default(self):
        assert mock_complete(user("buy 5 tsla")).trades[0].ticker == "AAPL"

    def test_buy_wins_over_sell(self):
        reply = mock_complete(user("buy AAPL, do not sell it"))
        assert reply.trades[0].side == "buy"


class TestSellBranch:
    """'sell' produces exactly one sell trade."""

    def test_sell_trade(self):
        reply = mock_complete(user("sell 4 MSFT please"))
        assert reply.message == "Selling 4 MSFT at market."
        assert len(reply.trades) == 1
        assert (reply.trades[0].side, reply.trades[0].quantity) == ("sell", 4.0)

    def test_sell_wins_over_watch(self):
        reply = mock_complete(user("sell NFLX and stop watching it"))
        assert reply.trades[0].side == "sell"


class TestWatchlistBranch:
    """'watch' or 'add' produces a watchlist add."""

    def test_watch_keyword(self):
        reply = mock_complete(user("watch PYPL"))
        assert reply.message == "Added PYPL to your watchlist."
        assert reply.trades == []
        change = reply.watchlist_changes[0]
        assert (change.ticker, change.action) == ("PYPL", "add")

    def test_add_keyword(self):
        reply = mock_complete(user("add PYPL to my watchlist"))
        assert reply.watchlist_changes[0].ticker == "PYPL"

    def test_default_ticker(self):
        assert mock_complete(user("add a ticker")).watchlist_changes[0].ticker == "AAPL"


class TestAnalysisBranch:
    """Anything else is a plain message with no actions."""

    def test_plain_analysis(self):
        reply = mock_complete(user("how is my portfolio doing?"))
        assert reply.message == ANALYSIS_MESSAGE
        assert reply.trades == []
        assert reply.watchlist_changes == []

    def test_deterministic(self):
        first = mock_complete(user("buy 10 AAPL"))
        second = mock_complete(user("buy 10 AAPL"))
        assert first.model_dump() == second.model_dump()


class TestMessageSelection:
    """The rules key off the last user message only."""

    def test_last_user_message_wins(self):
        messages = [
            {"role": "user", "content": "buy 10 AAPL"},
            {"role": "assistant", "content": "done"},
            {"role": "user", "content": "how am I doing?"},
        ]
        assert mock_complete(messages).message == ANALYSIS_MESSAGE

    def test_assistant_history_ignored(self):
        messages = [
            {"role": "assistant", "content": "you should buy 99 NVDA"},
            {"role": "user", "content": "no thanks"},
        ]
        assert mock_complete(messages).trades == []

    def test_no_user_message(self):
        assert mock_complete([{"role": "system", "content": "sys"}]).message == ANALYSIS_MESSAGE

    def test_empty_messages(self):
        assert mock_complete([]).message == ANALYSIS_MESSAGE
