"""LiteLLM client: OpenRouter with Cerebras as the inference provider."""

from __future__ import annotations

import logging
import os

import litellm
from pydantic import ValidationError

from .mock import mock_complete
from .schema import AssistantReply

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}
REASONING_EFFORT = "low"


class LLMError(Exception):
    """The LLM call failed, or its response did not match AssistantReply."""


def mock_enabled() -> bool:
    """Read LLM_MOCK at call time so tests and startup order cannot disagree."""
    return os.environ.get("LLM_MOCK", "").strip().lower() == "true"


def complete(messages: list[dict]) -> AssistantReply:
    """Send a chat conversation to the model and return the parsed structured reply.

    Returns a deterministic mock reply when LLM_MOCK=true. Raises LLMError on a
    network or API failure, an empty response, or a response that does not parse.
    """
    if mock_enabled():
        return mock_complete(messages)

    try:
        response = litellm.completion(
            model=MODEL,
            messages=messages,
            response_format=AssistantReply,
            reasoning_effort=REASONING_EFFORT,
            extra_body=EXTRA_BODY,
        )
        content = response.choices[0].message.content
    except Exception as exc:
        logger.warning("LLM request failed: %s", exc)
        raise LLMError(f"LLM request failed: {exc}") from exc

    if not content:
        raise LLMError("LLM returned an empty response")

    try:
        return AssistantReply.model_validate_json(content)
    except ValidationError as exc:
        logger.warning("LLM response did not match the schema: %s", exc)
        raise LLMError(f"LLM response did not match the expected schema: {exc}") from exc
