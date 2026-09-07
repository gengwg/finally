"""Portfolio snapshots."""

from app.db import list_snapshots, record_snapshot


def test_record_returns_the_stored_snapshot(db):
    snapshot = record_snapshot(10000.0)
    assert list_snapshots() == [snapshot]
    assert snapshot.to_dict() == {
        "total_value": 10000.0,
        "recorded_at": snapshot.recorded_at,
    }


def test_listed_oldest_first(db):
    for value in (100.0, 200.0, 300.0):
        record_snapshot(value)
    assert [s.total_value for s in list_snapshots()] == [100.0, 200.0, 300.0]


def test_limit_keeps_the_newest_in_chronological_order(db):
    for value in (100.0, 200.0, 300.0, 400.0):
        record_snapshot(value)
    assert [s.total_value for s in list_snapshots(limit=2)] == [300.0, 400.0]


def test_empty(db):
    assert list_snapshots() == []
