"""Tests for the LiteLLM client: call arguments, parsing, and mock routing."""

from types import SimpleNamespace

import pytest

from app.llm import client
from app.llm.client import EXTRA_BODY, MODEL, LLMError, complete
from app.llm.schema import AssistantReply

MESSAGES = [{"role": "system", "content": "sys"}, {"role": "user", "content": "buy 10 AAPL"}]

VALID_JSON = (
    '{"message": "Bought 10 AAPL.", '
    '"trades": [{"ticker": "aapl", "side": "buy", "quantity": 10}], '
    '"watchlist_changes": []}'
)


def fake_response(content):
    """Shape of a LiteLLM ModelResponse, only the bits the client reads."""
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture(autouse=True)
def live_mode(monkeypatch):
    """Default every test to the real code path; mock routing tests opt back in."""
    monkeypatch.delenv("LLM_MOCK", raising=False)


@pytest.fixture
def calls(monkeypatch):
    """Capture litellm.completion kwargs and return a canned response."""
    recorded = []

    def spy(**kwargs):
        recorded.append(kwargs)
        return fake_response(VALID_JSON)

    monkeypatch.setattr(client.litellm, "completion", spy)
    return recorded


class TestCallArguments:
    """Getting these wrong is the failure mode that matters."""

    def test_model_and_messages(self, calls):
        complete(MESSAGES)
        assert calls[0]["model"] == MODEL == "openrouter/openai/gpt-oss-120b"
        assert calls[0]["messages"] is MESSAGES

    def test_structured_output_target(self, calls):
        complete(MESSAGES)
        assert calls[0]["response_format"] is AssistantReply

    def test_cerebras_provider_order(self, calls):
        complete(MESSAGES)
        assert calls[0]["extra_body"] == {"provider": {"order": ["cerebras"]}}
        assert EXTRA_BODY == {"provider": {"order": ["cerebras"]}}

    def test_reasoning_effort(self, calls):
        complete(MESSAGES)
        assert calls[0]["reasoning_effort"] == "low"

    def test_called_once_no_retry(self, calls):
        complete(MESSAGES)
        assert len(calls) == 1


class TestResponseParsing:
    """The client returns a validated AssistantReply or raises LLMError."""

    def test_valid_response_parsed(self, calls):
        reply = complete(MESSAGES)
        assert reply.message == "Bought 10 AAPL."
        assert reply.trades[0].ticker == "AAPL"

    def test_message_only_response(self, monkeypatch):
        monkeypatch.setattr(
            client.litellm, "completion", lambda **_: fake_response('{"message": "Looks fine."}')
        )
        reply = complete(MESSAGES)
        assert reply.trades == []
        assert reply.watchlist_changes == []

    def test_malformed_json(self, monkeypatch):
        monkeypatch.setattr(
            client.litellm, "completion", lambda **_: fake_response('{"message": "oops"')
        )
        with pytest.raises(LLMError, match="did not match"):
            complete(MESSAGES)

    def test_prose_instead_of_json(self, monkeypatch):
        monkeypatch.setattr(
            client.litellm, "completion", lambda **_: fake_response("Sure, I bought it!")
        )
        with pytest.raises(LLMError):
            complete(MESSAGES)

    def test_partial_json_missing_message(self, monkeypatch):
        monkeypatch.setattr(
            client.litellm, "completion", lambda **_: fake_response('{"trades": []}')
        )
        with pytest.raises(LLMError):
            complete(MESSAGES)

    def test_invalid_side_rejected(self, monkeypatch):
        payload = '{"message": "x", "trades": [{"ticker": "AAPL", "side": "short", "quantity": 1}]}'
        monkeypatch.setattr(client.litellm, "completion", lambda **_: fake_response(payload))
        with pytest.raises(LLMError):
            complete(MESSAGES)

    def test_empty_content(self, monkeypatch):
        monkeypatch.setattr(client.litellm, "completion", lambda **_: fake_response(""))
        with pytest.raises(LLMError, match="empty"):
            complete(MESSAGES)

    def test_none_content(self, monkeypatch):
        monkeypatch.setattr(client.litellm, "completion", lambda **_: fake_response(None))
        with pytest.raises(LLMError, match="empty"):
            complete(MESSAGES)


class TestApiFailure:
    """Transport and API errors surface as LLMError."""

    def test_exception_wrapped(self, monkeypatch):
        def boom(**_):
            raise ConnectionError("openrouter unreachable")

        monkeypatch.setattr(client.litellm, "completion", boom)
        with pytest.raises(LLMError, match="openrouter unreachable") as exc_info:
            complete(MESSAGES)
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    def test_malformed_response_object(self, monkeypatch):
        monkeypatch.setattr(client.litellm, "completion", lambda **_: SimpleNamespace(choices=[]))
        with pytest.raises(LLMError):
            complete(MESSAGES)


class TestMockRouting:
    """LLM_MOCK is read at call time, so tests can flip it mid-process."""

    def test_mock_true_skips_litellm(self, monkeypatch):
        def fail(**_):
            raise AssertionError("litellm must not be called in mock mode")

        monkeypatch.setattr(client.litellm, "completion", fail)
        monkeypatch.setenv("LLM_MOCK", "true")
        reply = complete(MESSAGES)
        assert reply.trades[0].ticker == "AAPL"
        assert reply.message == "Buying 10 AAPL at market."

    def test_mock_value_is_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", " TRUE ")
        assert client.mock_enabled() is True

    def test_mock_false_uses_litellm(self, calls, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "false")
        complete(MESSAGES)
        assert len(calls) == 1

    def test_mock_unset_uses_litellm(self, calls):
        complete(MESSAGES)
        assert len(calls) == 1

    def test_toggled_between_calls(self, calls, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        assert complete(MESSAGES).message == "Buying 10 AAPL at market."
        monkeypatch.setenv("LLM_MOCK", "false")
        assert complete(MESSAGES).message == "Bought 10 AAPL."
        assert len(calls) == 1
