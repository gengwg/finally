"""/api/health and the /api/portfolio routes."""

import pytest

from app.db import get_cash_balance, get_position, record_snapshot

PORTFOLIO_KEYS = {
    "cash_balance",
    "positions",
    "positions_value",
    "total_value",
    "total_unrealized_pnl",
}


def test_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class TestGetPortfolio:
    def test_fresh_account(self, client):
        body = client.get("/api/portfolio").json()

        assert body == {
            "cash_balance": 10000.0,
            "positions": [],
            "positions_value": 0.0,
            "total_value": 10000.0,
            "total_unrealized_pnl": 0.0,
        }

    def test_reflects_a_held_position(self, client, cache):
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "buy"})
        cache.update("AAPL", 193.5)

        body = client.get("/api/portfolio").json()

        assert body["positions"] == [
            {
                "ticker": "AAPL",
                "quantity": 10.0,
                "avg_cost": 190.0,
                "current_price": 193.5,
                "market_value": 1935.0,
                "unrealized_pnl": 35.0,
                "pnl_percent": 1.84,
            }
        ]
        assert body["cash_balance"] == 8100.0
        assert body["total_value"] == 10035.0


class TestTrade:
    def test_buy(self, client):
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "aapl", "quantity": 10, "side": "buy"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["trade"]["ticker"] == "AAPL"
        assert body["trade"]["side"] == "buy"
        assert body["trade"]["quantity"] == 10.0
        assert body["trade"]["price"] == 190.0
        assert body["trade"]["id"]
        assert body["trade"]["executed_at"]
        assert PORTFOLIO_KEYS == set(body["portfolio"])
        assert body["portfolio"]["cash_balance"] == 8100.0
        assert get_cash_balance() == 8100.0

    def test_sell(self, client):
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "buy"})

        body = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "sell"}
        ).json()

        assert body["trade"]["side"] == "sell"
        assert body["portfolio"]["positions"] == []
        assert body["portfolio"]["cash_balance"] == 10000.0
        assert get_position("AAPL") is None

    def test_insufficient_cash_is_400(self, client):
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1000, "side": "buy"}
        )

        assert response.status_code == 400
        assert "Insufficient cash" in response.json()["detail"]
        assert get_cash_balance() == 10000.0

    def test_insufficient_shares_is_400(self, client):
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"}
        )

        assert response.status_code == 400
        assert "Insufficient shares" in response.json()["detail"]

    @pytest.mark.parametrize("quantity", [0, -3])
    def test_non_positive_quantity_is_400(self, client, quantity):
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": quantity, "side": "buy"}
        )

        assert response.status_code == 400
        assert "greater than zero" in response.json()["detail"]

    def test_bad_side_is_400(self, client):
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "short"}
        )

        assert response.status_code == 400
        assert "Invalid side" in response.json()["detail"]

    def test_unpriced_ticker_is_400(self, client):
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"}
        )

        assert response.status_code == 400
        assert "No price available" in response.json()["detail"]

    def test_missing_field_is_422(self, client):
        assert client.post("/api/portfolio/trade", json={"ticker": "AAPL"}).status_code == 422

    def test_trade_writes_a_snapshot(self, client):
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "buy"})

        snapshots = client.get("/api/portfolio/history").json()["snapshots"]
        assert len(snapshots) == 1
        assert snapshots[0]["total_value"] == 10000.0

    def test_buy_puts_the_ticker_on_the_watchlist(self, client, cache):
        cache.update("PYPL", 60.0)
        client.post("/api/portfolio/trade", json={"ticker": "PYPL", "quantity": 1, "side": "buy"})

        tickers = [row["ticker"] for row in client.get("/api/watchlist").json()["tickers"]]
        assert "PYPL" in tickers


class TestHistory:
    def test_empty(self, client):
        assert client.get("/api/portfolio/history").json() == {"snapshots": []}

    def test_oldest_first(self, client, cache):
        record_snapshot(10000.0)
        cache.update("AAPL", 191.0)
        record_snapshot(10100.0)
        record_snapshot(10200.0)

        snapshots = client.get("/api/portfolio/history").json()["snapshots"]

        assert [s["total_value"] for s in snapshots] == [10000.0, 10100.0, 10200.0]
        assert set(snapshots[0]) == {"total_value", "recorded_at"}

    def test_limit_returns_the_most_recent(self, client):
        for value in (1.0, 2.0, 3.0):
            record_snapshot(value)

        snapshots = client.get("/api/portfolio/history?limit=2").json()["snapshots"]

        assert [s["total_value"] for s in snapshots] == [2.0, 3.0]

    @pytest.mark.parametrize("limit", [0, -1, 99999])
    def test_out_of_range_limit_is_clamped(self, client, limit):
        record_snapshot(10000.0)

        response = client.get(f"/api/portfolio/history?limit={limit}")

        assert response.status_code == 200
        assert len(response.json()["snapshots"]) == 1

    def test_non_numeric_limit_is_422(self, client):
        assert client.get("/api/portfolio/history?limit=abc").status_code == 422
