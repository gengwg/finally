"""Tests for the system prompt and the portfolio context block."""

from app.llm.prompt import SYSTEM_PROMPT, render_portfolio_context

PORTFOLIO = {
    "cash_balance": 8080.0,
    "positions": [
        {
            "ticker": "AAPL",
            "quantity": 10.0,
            "avg_cost": 192.0,
            "current_price": 193.5,
            "market_value": 1935.0,
            "unrealized_pnl": 15.0,
            "pnl_percent": 0.78,
        },
        {
            "ticker": "TSLA",
            "quantity": 2.5,
            "avg_cost": 250.0,
            "current_price": 240.0,
            "market_value": 600.0,
            "unrealized_pnl": -25.0,
            "pnl_percent": -4.0,
        },
    ],
    "positions_value": 2535.0,
    "total_value": 10615.0,
    "total_unrealized_pnl": -10.0,
}

WATCHLIST = [
    {
        "ticker": "AAPL",
        "added_at": "2026-09-07T12:00:00+00:00",
        "price": 193.5,
        "change_percent": 0.05,
    },
    {
        "ticker": "PYPL",
        "added_at": "2026-09-07T12:00:00+00:00",
        "price": None,
        "change_percent": None,
    },
]


class TestSystemPrompt:
    """The prompt has to carry the persona and the structured-output instruction."""

    def test_names_the_assistant(self):
        assert "FinAlly" in SYSTEM_PROMPT

    def test_mentions_the_action_fields(self):
        assert "trades" in SYSTEM_PROMPT
        assert "watchlist_changes" in SYSTEM_PROMPT

    def test_no_trailing_whitespace_lines(self):
        assert all(line == line.rstrip() for line in SYSTEM_PROMPT.splitlines())


class TestRenderPortfolioContext:
    """The rendered block must contain the numbers it was handed."""

    def test_headline_figures(self):
        block = render_portfolio_context(PORTFOLIO, WATCHLIST)
        assert "Cash balance: $8,080.00" in block
        assert "Positions value: $2,535.00" in block
        assert "Total value: $10,615.00" in block
        assert "Total unrealized P&L: $-10.00" in block

    def test_position_line(self):
        block = render_portfolio_context(PORTFOLIO, WATCHLIST)
        assert (
            "AAPL: 10 shares, avg cost $192.00, price $193.50, value $1,935.00, "
            "P&L $15.00 (+0.78%)" in block
        )

    def test_fractional_quantity_and_loss(self):
        block = render_portfolio_context(PORTFOLIO, WATCHLIST)
        assert "TSLA: 2.5 shares" in block
        assert "P&L $-25.00 (-4.00%)" in block

    def test_watchlist_with_and_without_price(self):
        block = render_portfolio_context(PORTFOLIO, WATCHLIST)
        assert "AAPL: $193.50 (+0.05%)" in block
        assert "PYPL: no price yet" in block

    def test_empty_portfolio(self):
        empty = {
            "cash_balance": 10000.0,
            "positions": [],
            "positions_value": 0.0,
            "total_value": 10000.0,
            "total_unrealized_pnl": 0.0,
        }
        block = render_portfolio_context(empty, [])
        assert "(none)" in block
        assert "(empty)" in block
        assert "Cash balance: $10,000.00" in block

    def test_sections_present(self):
        block = render_portfolio_context(PORTFOLIO, WATCHLIST)
        assert block.index("POSITIONS") < block.index("WATCHLIST")
