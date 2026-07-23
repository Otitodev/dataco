"""Grounded reasoning services — the core anti-hallucination logic, extracted
from the HTTP layer so the API routes, the scan agent, and the MCP server all
call the *same* implementation.

Two invariants live here and must be preserved by every caller:
  1. The LLM only ever sees facts retrieved from DataHub (``build_context``).
  2. Model output is filtered by the grounding guard to the retrieved assets,
     and confidence is computed from context completeness — never the model's
     self-report.
"""

from __future__ import annotations

import logging

from app.domain.confidence import ConfidenceContext, confidence_label
from app.domain.grounding import ground_assets
from app.integrations.datahub import DataHubClient
from app.integrations.llm import Explanation, LLMClient
from app.repository.models import BriefRecord
from app.repository.store import Repository

logger = logging.getLogger(__name__)


def _stub_llm() -> LLMClient:
    """The deterministic stub, used as a fallback when a real LLM call fails."""
    from app.integrations.llm import create_llm_client

    return create_llm_client(provider="stub")


def build_context(issue, datahub: DataHubClient) -> dict:
    """Assemble the grounded context bundle the LLM reasons over — asset
    metadata + lineage from DataHub, never invented facts."""
    asset = datahub.get_asset(issue.asset_id)
    lineage = datahub.get_lineage(issue.asset_id)
    return {
        "asset_name": issue.asset_name,
        "issue_type": issue.issue_type,
        "owner": (asset.owner if asset else issue.owner),
        "freshness": asset.freshness if asset else None,
        "tags": asset.tags if asset else [],
        "schema_fields": [
            {"name": f.name, "type": f.type}
            for f in (asset.schema_fields if asset else [])
        ],
        "upstream": [n.name for n in lineage.upstream],
        "downstream": [n.name for n in lineage.downstream],
        "blast_radius": len(lineage.downstream),
    }


def allowed_assets(context: dict) -> list[str]:
    """Every asset name the model is permitted to reference — drawn only from
    the retrieved context (the affected asset + its lineage)."""
    return [context["asset_name"], *context["upstream"], *context["downstream"]]


def rule_based_confidence(context: dict) -> str:
    """Confidence is computed from how complete the retrieved context is, NOT
    from the model's self-report."""
    return confidence_label(
        ConfidenceContext(
            owner_present=bool(context["owner"]),
            lineage_complete=bool(context["downstream"]),
        )
    )


def explain_issue(
    issue, *, repo: Repository, llm: LLMClient, datahub: DataHubClient
) -> Explanation:
    """Produce a grounded explanation and persist it on the issue."""
    context = build_context(issue, datahub)
    try:
        result = llm.explain(context)
    except Exception as exc:  # e.g. invalid/expired API key → don't 500 the scan
        logger.warning("LLM explain failed (%s); using deterministic stub.", exc)
        result = _stub_llm().explain(context)

    impacted = ground_assets(result.impacted_assets, allowed_assets(context))
    confidence = rule_based_confidence(context)

    repo.save_explanation(
        issue.id,
        summary=result.summary,
        likely_cause=result.likely_cause,
        impacted_assets=impacted,
        confidence=confidence,
        blast_radius=context["blast_radius"] or None,
    )

    return Explanation(
        summary=result.summary,
        likely_cause=result.likely_cause,
        impacted_assets=impacted,
        confidence=confidence,
        recommended_action=result.recommended_action,
    )


def brief_issue(
    issue, *, repo: Repository, llm: LLMClient, datahub: DataHubClient
) -> BriefRecord:
    """Produce a grounded stakeholder brief and persist it."""
    context = build_context(issue, datahub)
    try:
        result = llm.brief(context)
    except Exception as exc:  # invalid/expired API key → fall back, don't crash
        logger.warning("LLM brief failed (%s); using deterministic stub.", exc)
        result = _stub_llm().brief(context)

    affected = ground_assets(result.what_is_affected, allowed_assets(context))

    brief = BriefRecord(
        issue_id=issue.id,
        subject=result.subject,
        what_happened=result.what_happened,
        who_to_contact=result.who_to_contact,
        next_step=result.next_step,
        estimated_impact=result.estimated_impact,
    )
    brief.set_affected(affected)
    return repo.create_brief(brief)
