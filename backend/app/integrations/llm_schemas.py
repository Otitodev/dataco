"""Provider-agnostic pieces shared by every LLMClient implementation:
the structured-output schemas, the grounding-first system prompts, and the
mappers back to the domain ``Explanation`` / ``Brief`` types.

Kept separate so the Anthropic and OpenAI modules don't import each other.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.integrations.llm import Brief, Explanation

Confidence = Literal["high", "medium", "low"]
Impact = Literal["low", "medium", "high", "critical"]


class ExplanationOut(BaseModel):
    # extra="forbid" -> additionalProperties:false, required for OpenAI strict schemas.
    model_config = ConfigDict(extra="forbid")

    summary: str
    likely_cause: str
    impacted_assets: list[str]
    confidence: Confidence
    recommended_action: str


class BriefOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    what_happened: str
    what_is_affected: list[str]
    who_to_contact: str
    next_step: str
    estimated_impact: Impact


EXPLAIN_SYSTEM = (
    "You are Dataco's data-trust analyst. You explain why a healthcare dataset "
    "may be unreliable, using ONLY the metadata and lineage provided in the "
    "user message. Never invent owners, assets, causes, or numbers that are not "
    "present in the context. If a fact is missing, say so rather than guessing. "
    "Set `impacted_assets` only to downstream assets named in the context. "
    "Choose `confidence` based on how complete the context is: 'high' when the "
    "owner and lineage are both present, 'low' when either is missing."
)

BRIEF_SYSTEM = (
    "You write a plain-language stakeholder brief for a non-technical healthcare "
    "leader (e.g. a clinical director), grounded ONLY in the metadata and lineage "
    "provided. Never invent facts. Keep `what_happened` to 2-3 plain sentences "
    "with no jargon. `what_is_affected` must list only downstream assets named in "
    "the context, using human-readable names. `estimated_impact` reflects the "
    "blast radius and severity. Be calm, specific, and actionable."
)


def render_context(context: dict) -> str:
    return (
        "Here is the retrieved DataHub context for the affected asset. "
        "Base your entire response on it and nothing else:\n\n"
        + json.dumps(context, default=str, indent=2, sort_keys=True)
    )


def to_explanation(out: ExplanationOut) -> Explanation:
    return Explanation(
        summary=out.summary,
        likely_cause=out.likely_cause,
        impacted_assets=out.impacted_assets,
        confidence=out.confidence,
        recommended_action=out.recommended_action,
    )


def to_brief(out: BriefOut) -> Brief:
    return Brief(
        subject=out.subject,
        what_happened=out.what_happened,
        what_is_affected=out.what_is_affected,
        who_to_contact=out.who_to_contact,
        next_step=out.next_step,
        estimated_impact=out.estimated_impact,
    )


class LLMError(RuntimeError):
    """Raised when a model returns no parseable structured output."""
