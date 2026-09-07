"""Fixtures for the database tests: a real SQLite file per test, no mocks."""

import pytest

from app.db import init_db


@pytest.fixture(autouse=True)
def db_env(tmp_path, monkeypatch):
    """Point DB_PATH at a fresh file inside tmp_path. No schema created yet."""
    path = tmp_path / "nested" / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    return path


@pytest.fixture
def db(db_env):
    """An initialised, seeded database."""
    init_db()
    return db_env
