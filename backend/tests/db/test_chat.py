"""Chat history and the actions JSON column."""

from app.db import add_chat_message, list_chat_messages


def test_actions_round_trip_as_a_dict(db):
    actions = {
        "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
        "watchlist_changes": [],
    }
    add_chat_message("assistant", "Bought 10 AAPL.", actions)

    stored = list_chat_messages()[0]
    assert stored.actions == actions


def test_actions_default_to_none(db):
    message = add_chat_message("user", "how am I doing?")
    assert message.actions is None
    assert list_chat_messages()[0].actions is None


def test_listed_oldest_first(db):
    add_chat_message("user", "one")
    add_chat_message("assistant", "two")
    add_chat_message("user", "three")
    assert [m.content for m in list_chat_messages()] == ["one", "two", "three"]


def test_limit_keeps_the_newest_in_chronological_order(db):
    for i in range(4):
        add_chat_message("user", str(i))
    assert [m.content for m in list_chat_messages(limit=2)] == ["2", "3"]


def test_to_dict(db):
    message = add_chat_message("assistant", "hi", {"trades": []})
    assert message.to_dict() == {
        "id": message.id,
        "role": "assistant",
        "content": "hi",
        "actions": {"trades": []},
        "created_at": message.created_at,
    }
