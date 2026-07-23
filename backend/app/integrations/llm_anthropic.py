"""Anthropic (Claude) implementation of the LLMClient protocol.

Isolated so importing ``app.integrations.llm`` never requires the ``anthropic``
SDK — the factory imports this lazily only when constructing a real client.
"""

from __future__ import annotations

from typing import TypeVar

import anthropic
from pydantic import BaseModel

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_DEFAULT_MODEL
from app.integrations.llm import Brief, Explanation
from app.integrations.llm_schemas import (
    BRIEF_SYSTEM,
    EXPLAIN_SYSTEM,
    BriefOut,
    ExplanationOut,
    LLMError,
    render_context,
    to_brief,
    to_explanation,
)

_T = TypeVar("_T", bound=BaseModel)


class AnthropicLLMClient:
    """Claude-backed LLMClient. Satisfies the ``LLMClient`` protocol."""

    def __init__(
        self,
        model: str = ANTHROPIC_DEFAULT_MODEL,
        api_key: str | None = None,
        max_tokens: int = 2048,
    ) -> None:
        # api_key=None lets the SDK resolve ANTHROPIC_API_KEY / an auth profile.
        self._client = anthropic.Anthropic(api_key=api_key or ANTHROPIC_API_KEY or None)
        self._model = model
        self._max_tokens = max_tokens

    def explain(self, context: dict) -> Explanation:
        return to_explanation(self._parse(EXPLAIN_SYSTEM, context, ExplanationOut))

    def brief(self, context: dict) -> Brief:
        return to_brief(self._parse(BRIEF_SYSTEM, context, BriefOut))

    def _parse(self, system: str, context: dict, schema: type[_T]) -> _T:
        message = self._client.messages.parse(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": render_context(context)}],
            output_format=schema,
        )
        if message.parsed_output is None:
            raise LLMError(
                f"Claude returned no parseable output "
                f"(stop_reason={message.stop_reason})"
            )
        return message.parsed_output
