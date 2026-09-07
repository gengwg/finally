"""The /api/chat routes."""

from app.db import upsert_position

BUY_10_AAPL = [{"ticker": "AAPL", "side": "buy", "quantity": 10}]


class TestPostChat:
    def test_successful_turn(self, client, model):
        model.set(message="Bought 10 AAPL.", trades=BUY_10_AAPL)

        response = client.post("/api/chat", json={"message": "buy 10 AAPL"})

        assert response.status_code == 200
        body = response.json()
        assert body["message"] == "Bought 10 AAPL."
        assert body["trades"][0]["status"] == "executed"
        assert body["watchlist_changes"] == []
        assert body["portfolio"]["cash_balance"] == 8100.0

    def test_rejected_trade_is_still_a_200(self, client, model):
        model.set(trades=[{"ticker": "AAPL", "side": "buy", "quantity": 1000}])

        response = client.post("/api/chat", json={"message": "buy 1000 AAPL"})

        assert response.status_code == 200
        trade = response.json()["trades"][0]
        assert trade["status"] == "failed"
        assert "Insufficient cash" in trade["error"]

    def test_llm_failure_is_a_502(self, client, model):
        model.fail(ConnectionError("openrouter unreachable"))

        response = client.post("/api/chat", json={"message": "hello"})

        assert response.status_code == 502
        assert "openrouter unreachable" in response.json()["detail"]

    def test_unparseable_reply_is_a_502(self, client, model):
        model.raw("not json at all")

        assert client.post("/api/chat", json={"message": "hello"}).status_code == 502

    def test_empty_message_is_a_400(self, client, model):
        response = client.post("/api/chat", json={"message": "   "})

        assert response.status_code == 400
        assert response.json()["detail"] == "Message cannot be empty"
        assert model.calls == []

    def test_missing_message_is_a_422(self, client, model):
        assert client.post("/api/chat", json={}).status_code == 422

    def test_message_is_trimmed_before_use(self, client, model):
        client.post("/api/chat", json={"message": "  how am I doing?  "})

        assert model.messages[-1]["content"] == "how am I doing?"


class TestPriceFeedSync:
    """A watchlist edit from the assistant must move the price feed with it."""

    def test_add_starts_streaming(self, client, model, source):
        model.set(watchlist_changes=[{"ticker": "PYPL", "action": "add"}])

        client.post("/api/chat", json={"message": "watch PYPL"})

        assert "PYPL" in source.get_tickers()

    def test_remove_stops_streaming(self, client, model, source):
        model.set(watchlist_changes=[{"ticker": "AAPL", "action": "remove"}])

        client.post("/api/chat", json={"message": "drop AAPL"})

        assert "AAPL" not in source.get_tickers()

    def test_remove_keeps_streaming_what_we_own(self, client, model, source):
        upsert_position("AAPL", 5.0, 190.0)
        model.set(watchlist_changes=[{"ticker": "AAPL", "action": "remove"}])

        client.post("/api/chat", json={"message": "drop AAPL"})

        assert "AAPL" in source.get_tickers()

    def test_failed_change_leaves_the_feed_alone(self, client, model, source):
        before = source.get_tickers()
        model.set(watchlist_changes=[{"ticker": "AAPL", "action": "add"}])

        client.post("/api/chat", json={"message": "watch AAPL"})

        assert source.get_tickers() == before


class TestChatHistory:
    def test_empty_history(self, client):
        assert client.get("/api/chat/history").json() == {"messages": []}

    def test_oldest_first_with_actions(self, client, model):
        model.set(message="Bought.", trades=BUY_10_AAPL)
        client.post("/api/chat", json={"message": "buy 10 AAPL"})

        messages = client.get("/api/chat/history").json()["messages"]

        assert [m["role"] for m in messages] == ["user", "assistant"]
        assert messages[0]["content"] == "buy 10 AAPL"
        assert messages[0]["actions"] is None
        assert messages[1]["actions"]["trades"][0]["status"] == "executed"

    def test_actions_survive_the_db_round_trip_verbatim(self, client, model):
        """A reloaded conversation must render the same chips the live one did."""
        model.set(
            message="Two of three went through.",
            trades=[
                {"ticker": "AAPL", "side": "buy", "quantity": 10},
                {"ticker": "MSFT", "side": "buy", "quantity": 500},
            ],
            watchlist_changes=[{"ticker": "AAPL", "action": "add"}],
        )
        live = client.post("/api/chat", json={"message": "buy 10 AAPL and 500 MSFT"}).json()

        reloaded = client.get("/api/chat/history").json()["messages"][1]["actions"]

        assert reloaded == {
            "trades": live["trades"],
            "watchlist_changes": live["watchlist_changes"],
        }
        assert reloaded["trades"][0]["price"] == 190.0
        assert reloaded["trades"][0]["error"] is None
        failed = reloaded["trades"][1]
        assert failed["status"] == "failed"
        assert failed["price"] is None
        assert "Insufficient cash" in failed["error"]
        assert reloaded["watchlist_changes"][0]["status"] == "failed"
        assert "already on the watchlist" in reloaded["watchlist_changes"][0]["error"]

    def test_row_shape(self, client, model):
        client.post("/api/chat", json={"message": "hello"})

        row = client.get("/api/chat/history").json()["messages"][0]

        assert set(row) == {"id", "role", "content", "actions", "created_at"}
        assert row["id"]
        assert row["created_at"]

    def test_limit_returns_the_most_recent(self, client, model):
        for text in ("one", "two", "three"):
            client.post("/api/chat", json={"message": text})

        messages = client.get("/api/chat/history?limit=2").json()["messages"]

        assert [m["content"] for m in messages] == ["three", "ok"]

    def test_limit_is_clamped(self, client, model):
        client.post("/api/chat", json={"message": "hello"})

        assert client.get("/api/chat/history?limit=0").status_code == 200
        assert client.get("/api/chat/history?limit=99999").status_code == 200


class TestMockMode:
    """What the E2E suite sees with LLM_MOCK=true."""

    def test_buy_through_the_route(self, client, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")

        body = client.post("/api/chat", json={"message": "buy 10 AAPL"}).json()

        assert body["message"] == "Buying 10 AAPL at market."
        assert body["trades"][0]["status"] == "executed"
        assert body["portfolio"]["cash_balance"] == 8100.0

    def test_watchlist_add_through_the_route(self, client, source, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")

        body = client.post("/api/chat", json={"message": "add PYPL to my watchlist"}).json()

        assert body["watchlist_changes"][0] == {
            "ticker": "PYPL",
            "action": "add",
            "status": "executed",
            "error": None,
        }
        assert "PYPL" in source.get_tickers()
