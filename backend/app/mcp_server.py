"""Dataco MCP server — exposes the data-trust agent's tools over the Model
Context Protocol so any MCP client (Claude Desktop, IDEs, other agents) can
drive it directly, not just the HTTP API.

Every tool reuses the same service functions the FastAPI routes call, so the
grounding/write-back invariants hold identically over MCP. Each tool opens its
own DB session (MCP tools are independent calls) and resolves the DataHub/LLM
clients through the normal provider factories — so it runs offline on the fake
and live when a token is configured.

Run:  python -m app.mcp_server   (requires the ``mcp`` extra: pip install -e ".[mcp]")
"""

from __future__ import annotations

from contextlib import contextmanager

from mcp.server.fastmcp import FastMCP

from app.deps import SessionLocal, get_datahub, get_llm
from app.repository.store import Repository
from app.services.reasoning import brief_issue, explain_issue
from app.services.scan import scan_asset
from app.services.writeback import write_back_issue

mcp = FastMCP("dataco")


@contextmanager
def _repo():
    session = SessionLocal()
    try:
        yield Repository(session)
    finally:
        session.close()


@mcp.tool()
def list_issues() -> list[dict]:
    """List active/investigating data-trust issues Dataco is tracking."""
    with _repo() as repo:
        return [
            {
                "id": i.id,
                "asset_name": i.asset_name,
                "issue_type": i.issue_type,
                "severity": i.severity,
                "status": i.status,
                "blast_radius": i.blast_radius,
                "confidence": i.confidence,
            }
            for i in repo.list_active_issues()
        ]


@mcp.tool()
def search_assets(query: str) -> list[dict]:
    """Search DataHub for assets matching a query."""
    datahub = get_datahub()
    return [
        {"urn": a.urn, "name": a.name, "owner": a.owner}
        for a in datahub.search(query)
    ]


@mcp.tool()
def scan_asset_tool(urn: str) -> dict:
    """Scan a DataHub asset for trust issues; if found, explain it and write a
    tag + assertion back to DataHub. Returns the scan result."""
    datahub = get_datahub()
    llm = get_llm()
    with _repo() as repo:
        result = scan_asset(urn, datahub=datahub, repo=repo, llm=llm)
        return vars(result)


@mcp.tool()
def explain_issue_tool(issue_id: str) -> dict:
    """Produce a grounded explanation for an existing issue."""
    datahub = get_datahub()
    llm = get_llm()
    with _repo() as repo:
        issue = repo.get_issue(issue_id)
        if issue is None:
            return {"error": "issue not found"}
        result = explain_issue(issue, repo=repo, llm=llm, datahub=datahub)
        return {
            "summary": result.summary,
            "likely_cause": result.likely_cause,
            "impacted_assets": result.impacted_assets,
            "confidence": result.confidence,
            "recommended_action": result.recommended_action,
        }


@mcp.tool()
def generate_brief_tool(issue_id: str) -> dict:
    """Produce a grounded stakeholder brief for an existing issue."""
    datahub = get_datahub()
    llm = get_llm()
    with _repo() as repo:
        issue = repo.get_issue(issue_id)
        if issue is None:
            return {"error": "issue not found"}
        brief = brief_issue(issue, repo=repo, llm=llm, datahub=datahub)
        return {
            "subject": brief.subject,
            "what_happened": brief.what_happened,
            "what_is_affected": brief.get_affected(),
            "who_to_contact": brief.who_to_contact,
            "next_step": brief.next_step,
            "estimated_impact": brief.estimated_impact,
        }


@mcp.tool()
def annotate_datahub(issue_id: str) -> dict:
    """Write an existing issue back to DataHub as a tag + custom assertion."""
    datahub = get_datahub()
    with _repo() as repo:
        issue = repo.get_issue(issue_id)
        if issue is None:
            return {"error": "issue not found"}
        result = write_back_issue(datahub, issue)
        repo.save_writeback(
            issue.id, tag_urn=result.tag_urn, assertion_urn=result.assertion_urn
        )
        return {
            "ok": result.ok,
            "tag_urn": result.tag_urn,
            "assertion_urn": result.assertion_urn,
            "detail": result.detail,
        }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
