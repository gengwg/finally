"""App wiring: startup, shutdown, the snapshot loop and the static frontend."""

import time

from fastapi.testclient import TestClient

from app import main
from app.db import list_snapshots
from app.db.init import DEFAULT_WATCHLIST


def test_startup_starts_the_feed_with_the_watchlist(client, source):
    assert source.started
    assert source.get_tickers() == DEFAULT_WATCHLIST


def test_shutdown_stops_the_feed(app, source):
    with TestClient(app):
        assert not source.stopped

    assert source.stopped
    assert app.state.market_source is None


def test_stream_route_is_registered_once(app):
    paths = [route.path for route in app.routes]

    assert paths.count("/api/stream/prices") == 1


def test_building_the_app_twice_does_not_duplicate_routes(app):
    second = main.create_app()

    assert [route.path for route in app.routes] == [route.path for route in second.routes]


def test_snapshot_loop_records_portfolio_value(app, monkeypatch):
    monkeypatch.setattr(main, "SNAPSHOT_INTERVAL_SECONDS", 0.01)

    with TestClient(app):
        deadline = time.monotonic() + 5
        while not list_snapshots() and time.monotonic() < deadline:
            time.sleep(0.02)

    assert [snapshot.total_value for snapshot in list_snapshots()] == [10000.0]


class TestStaticFrontend:
    def test_missing_export_leaves_the_api_alone(self, client):
        assert client.get("/api/health").status_code == 200
        assert client.get("/").status_code == 404

    def test_export_is_served_with_an_index_fallback(self, tmp_path, monkeypatch, source):
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        (static_dir / "index.html").write_text("<h1>FinAlly</h1>")
        (static_dir / "app.js").write_text("console.log(1)")
        monkeypatch.setenv("DB_PATH", str(tmp_path / "finally.db"))
        monkeypatch.setenv("STATIC_DIR", str(static_dir))
        monkeypatch.setattr(main, "create_market_data_source", lambda cache: source)

        with TestClient(main.create_app()) as client:
            assert client.get("/").text == "<h1>FinAlly</h1>"
            assert "console.log" in client.get("/app.js").text
            # Client-side route: no such file, so the SPA shell is served.
            assert client.get("/positions").text == "<h1>FinAlly</h1>"
            # API typos stay honest 404s rather than returning HTML.
            assert client.get("/api/nope").status_code == 404
            assert client.get("/api/health").json() == {"status": "ok"}
