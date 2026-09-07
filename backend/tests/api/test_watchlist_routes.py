"""The /api/watchlist routes."""

import pytest

from app.db import DEFAULT_USER_ID, list_watchlist, upsert_position
from app.db.init import DEFAULT_WATCHLIST

ROW_KEYS = {
    "ticker",
    "added_at",
    "price",
    "previous_price",
    "change",
    "change_percent",
    "direction",
}


class TestGetWatchlist:
    def test_seeded_watchlist(self, client):
        rows = client.get("/api/watchlist").json()["tickers"]

        assert [row["ticker"] for row in rows] == DEFAULT_WATCHLIST
        assert set(rows[0]) == ROW_KEYS

    def test_priced_row_carries_the_cached_quote(self, client, cache):
        cache.update("AAPL", 193.5)

        rows = client.get("/api/watchlist").json()["tickers"]
        aapl = next(row for row in rows if row["ticker"] == "AAPL")

        assert aapl["price"] == 193.5
        assert aapl["previous_price"] == 190.0
        assert aapl["change"] == 3.5
        assert aapl["change_percent"] == pytest.approx(1.8421, abs=1e-4)
        assert aapl["direction"] == "up"
        assert aapl["added_at"]

    def test_unpriced_row_is_all_nulls(self, client):
        rows = client.get("/api/watchlist").json()["tickers"]
        tsla = next(row for row in rows if row["ticker"] == "TSLA")

        assert tsla["price"] is None
        assert tsla["previous_price"] is None
        assert tsla["change"] is None
        assert tsla["change_percent"] is None
        assert tsla["direction"] is None


class TestAddTicker:
    def test_adds_and_returns_the_full_list(self, client, source):
        response = client.post("/api/watchlist", json={"ticker": "pypl"})

        assert response.status_code == 201
        tickers = [row["ticker"] for row in response.json()["tickers"]]
        assert tickers == [*DEFAULT_WATCHLIST, "PYPL"]
        assert "PYPL" in source.get_tickers()

    def test_duplicate_is_409(self, client):
        response = client.post("/api/watchlist", json={"ticker": "AAPL"})

        assert response.status_code == 409
        assert response.json()["detail"] == "AAPL is already on the watchlist"
        assert len(list_watchlist()) == len(DEFAULT_WATCHLIST)

    @pytest.mark.parametrize("ticker", ["", "   ", "TOOLONG", "BRK.B", "12", "A B"])
    def test_invalid_symbol_is_400(self, client, ticker, source):
        response = client.post("/api/watchlist", json={"ticker": ticker})

        assert response.status_code == 400
        assert "Invalid ticker" in response.json()["detail"]
        assert len(list_watchlist()) == len(DEFAULT_WATCHLIST)
        assert source.get_tickers() == DEFAULT_WATCHLIST

    def test_missing_field_is_422(self, client):
        assert client.post("/api/watchlist", json={}).status_code == 422


class TestRemoveTicker:
    def test_removes_and_stops_the_feed(self, client, source):
        response = client.delete("/api/watchlist/AAPL")

        assert response.status_code == 200
        tickers = [row["ticker"] for row in response.json()["tickers"]]
        assert "AAPL" not in tickers
        assert "AAPL" not in source.get_tickers()

    def test_lower_case_path_works(self, client):
        assert client.delete("/api/watchlist/aapl").status_code == 200
        assert "AAPL" not in [entry.ticker for entry in list_watchlist()]

    def test_missing_ticker_is_404(self, client, source):
        response = client.delete("/api/watchlist/ZZZZ")

        assert response.status_code == 404
        assert response.json()["detail"] == "ZZZZ is not on the watchlist"
        assert source.get_tickers() == DEFAULT_WATCHLIST

    def test_open_position_keeps_the_price_feed(self, client, source):
        upsert_position("AAPL", 5, 190.0, user_id=DEFAULT_USER_ID)

        response = client.delete("/api/watchlist/AAPL")

        assert response.status_code == 200
        assert "AAPL" not in [row["ticker"] for row in response.json()["tickers"]]
        # Still priced, so the position keeps a current value.
        assert "AAPL" in source.get_tickers()
