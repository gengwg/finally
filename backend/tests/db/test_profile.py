"""Cash balance."""

from app.db import get_cash_balance, get_connection, set_cash_balance


def test_set_and_get(db):
    set_cash_balance(1234.56)
    assert get_cash_balance() == 1234.56


def test_unknown_user_has_no_cash(db):
    assert get_cash_balance(user_id="nobody") == 0.0


def test_set_creates_missing_profile(db):
    set_cash_balance(500.0, user_id="second")
    assert get_cash_balance(user_id="second") == 500.0
    assert get_cash_balance() == 10000.0


def test_shared_conn_is_not_committed_until_the_caller_commits(db):
    with get_connection() as conn:
        set_cash_balance(1.0, conn=conn)
        assert get_cash_balance() == 10000.0  # separate connection: still the seeded value
        conn.commit()
    assert get_cash_balance() == 1.0
