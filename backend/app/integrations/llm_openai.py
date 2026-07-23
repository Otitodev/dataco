"""OpenAI (GPT) implementation of the LLMClient protocol.

A sibling to the Anthropic client. Isolated so importing
``app.integrations.llm`` never requires the ``openai`` SDK — the factory
imports this lazily only when constructing a real client.

Uses Chat Completions structured outputs (strict JSON schema) rather than the
beta ``.parse`` helper, so it works across a wide range of SDK versions.
"""

from __future__ import annotations

from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.config import OPENAI_API_KEY, OPENAI_DEFAULT_MODEL
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


class OpenAILLMClient:
    """GPT-backed LLMClient. Satisfies the ``LLMClient`` protocol."""

    def __init__(
        self,
        model: str = OPENAI_DEFAULT_MODEL,
        api_key: str | None = None,
    ) -> None:
        # api_key=None lets the SDK resolve OPENAI_API_KEY from the environment.
        self._client = OpenAI(api_key=api_key or OPENAI_API_KEY or None)
        self._model = model

    def explain(self, context: dict) -> Explanation:
        return to_explanation(
            self._parse(EXPLAIN_SYSTEM, context, "explanation", ExplanationOut)
        )

    def brief(self, context: dict) -> Brief:
        return to_brief(self._parse(BRIEF_SYSTEM, context, "brief", BriefOut))

    def _parse(self, system: str, context: dict, name: str, schema: type[_T]) -> _T:
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": render_context(context)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": name,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
        )
        message = completion.choices[0].message
        if getattr(message, "refusal", None):
            raise LLMError(f"OpenAI refused the request: {message.refusal}")
        if not message.content:
            raise LLMError(
                f"OpenAI returned no content "
                f"(finish_reason={completion.choices[0].finish_reason})"
            )
        return schema.model_validate_json(message.content)
