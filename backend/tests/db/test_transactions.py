"""The optional conn keyword: one transaction across several tables."""

import pytest

from app.db import (
    add_to_watchlist,
    get_cash_balance,
    get_connection,
    get_position,
    list_trades,
    list_watchlist,
    record_trade,
    set_cash_balance,
    upsert_position,
)


def test_shared_conn_commits_everything_together(db):
    with get_connection() as conn:
        set_cash_balance(8100.0, conn=conn)
        upsert_position("AAPL", 10, 190.0, conn=conn)
        record_trade("AAPL", "buy", 10, 190.0, conn=conn)
        add_to_watchlist("PYPL", conn=conn)
        conn.commit()

    assert get_cash_balance() == 8100.0
    assert get_position("AAPL").quantity == 10
    assert len(list_trades()) == 1
    assert "PYPL" in [e.ticker for e in list_watchlist()]


def test_rollback_leaves_no_partial_writes(db):
    with pytest.raises(RuntimeError):
        with get_connection() as conn:
            set_cash_balance(8100.0, conn=conn)
            upsert_position("AAPL", 10, 190.0, conn=conn)
            record_trade("AAPL", "buy", 10, 190.0, conn=conn)
            raise RuntimeError("trade failed halfway")

    assert get_cash_balance() == 10000.0
    assert get_position("AAPL") is None
    assert list_trades() == []


def test_without_conn_each_call_commits_itself(db):
    upsert_position("AAPL", 10, 190.0)
    assert get_position("AAPL") is not None
