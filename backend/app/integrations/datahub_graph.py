"""Real DataHub implementation of the DataHubClient protocol.

Talks to a live DataHub instance through its stable GraphQL API (the same
contract the DataHub UI uses). The ``acryl-datahub`` SDK is imported lazily on
first use, so this module imports and constructs without the SDK installed —
mirroring the lazy-provider pattern used by the LLM clients.

Named ``DataHubGraphClient`` (not ``DataHubClient``) to avoid colliding with our
own ``DataHubClient`` protocol *and* with DataHub's own new SDK class of the
same name.

NOTE: the GraphQL queries below use canonical DataHub field names; validate them
against your DataHub version the first time you point this at a live instance
(`datahub docker quickstart`). Parsing is defensive so an unexpected shape
degrades to empty/None rather than raising.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from app.domain.types import AssetMeta, AssetNode, Field, Lineage

logger = logging.getLogger(__name__)

_SEARCH_QUERY = """
query search($q: String!) {
  search(input: { type: DATASET, query: $q, start: 0, count: 10 }) {
    searchResults {
      entity {
        urn
        ... on Dataset {
          name
          properties { name }
          ownership {
            owners { owner { ... on CorpUser { urn } ... on CorpGroup { urn } } }
          }
        }
      }
    }
  }
}
"""

_ASSET_QUERY = """
query dataset($urn: String!) {
  dataset(urn: $urn) {
    urn
    name
    properties { name description }
    editableProperties { description }
    ownership { owners { owner { ... on CorpUser { urn } ... on CorpGroup { urn } } } }
    schemaMetadata { fields { fieldPath nativeDataType } }
    tags { tags { tag { urn } } }
  }
}
"""

# Selection set shared by the batch query; mirrors the fields _ASSET_QUERY reads.
_DATASET_FIELDS = """
    urn
    name
    properties { name description }
    editableProperties { description }
    ownership { owners { owner { ... on CorpUser { urn } ... on CorpGroup { urn } } } }
    schemaMetadata { fields { fieldPath nativeDataType } }
    tags { tags { tag { urn } } }
"""

_LINEAGE_QUERY = """
query lineage($urn: String!) {
  dataset(urn: $urn) {
    upstream: lineage(input: { direction: UPSTREAM, start: 0, count: 100 }) {
      relationships {
        entity {
          urn
          ... on Dataset { name properties { name } }
          ... on Dashboard { info { name } }
          ... on Chart { info { name } }
          ... on DataJob { jobId }
          ... on DataFlow { flowId }
          ... on MLModel { name }
        }
      }
    }
    downstream: lineage(input: { direction: DOWNSTREAM, start: 0, count: 100 }) {
      relationships {
        entity {
          urn
          ... on Dataset { name properties { name } }
          ... on Dashboard { info { name } }
          ... on Chart { info { name } }
          ... on DataJob { jobId }
          ... on DataFlow { flowId }
          ... on MLModel { name }
        }
      }
    }
  }
}
"""

_ADD_TAGS_MUTATION = """
mutation addTags($tagUrn: String!, $resourceUrn: String!) {
  addTags(input: { tagUrns: [$tagUrn], resourceUrn: $resourceUrn })
}
"""

# Report the assertion result WITHOUT the newer `severity` field (unsupported on
# older DataHub servers, e.g. quickstart v1.5.x); severity rides along as a
# property instead, which older AssertionResultInput schemas accept.
_REPORT_RESULT_MUTATION = """
mutation reportResult(
  $urn: String!, $ts: Long!, $type: AssertionResultType!,
  $props: [StringMapEntryInput!]
) {
  reportAssertionResult(
    urn: $urn, result: { timestampMillis: $ts, type: $type, properties: $props }
  )
}
"""


class DataHubGraphClient:
    """DataHub-backed DataHubClient. Satisfies the ``DataHubClient`` protocol."""

    def __init__(self, server: str, token: str | None = None) -> None:
        self._server = server
        self._token = token
        self._graph_client: Any | None = None  # built lazily on first call

    # --- SDK is imported only here, so construction stays offline-safe --------
    def _graph(self) -> Any:
        if self._graph_client is None:
            from datahub.ingestion.graph.client import DatahubClientConfig, DataHubGraph

            self._graph_client = DataHubGraph(
                DatahubClientConfig(server=self._server, token=self._token or None)
            )
        return self._graph_client

    def _run(self, query: str, variables: dict) -> dict | None:
        """Run a GraphQL query, degrading a not-found ``GraphError`` to ``None``.

        DataHub raises ``GraphError`` (HTTP 400 BAD_REQUEST) when a URN names an
        entity it doesn't know — the read protocol promises a graceful miss
        (``None``/empty), not a 500. Genuine errors (bad query, auth) re-raise.
        The SDK is not imported here (``_is_not_found`` matches by class name),
        so the offline mapping tests run without ``acryl-datahub`` installed.
        """
        try:
            return self._graph().execute_graphql(query, variables=variables)
        except Exception as exc:
            if _is_not_found(exc):
                logger.warning("DataHub entity not found (%s): %s", variables, exc)
                return None
            raise

    # --- protocol methods (read) ---------------------------------------------
    def search(self, query: str) -> list[AssetMeta]:
        data = self._run(_SEARCH_QUERY, variables={"q": query})
        results = _dig(data, "search", "searchResults") or []
        assets: list[AssetMeta] = []
        for r in results:
            entity = r.get("entity") or {}
            urn = entity.get("urn")
            if not urn:
                continue
            assets.append(
                AssetMeta(
                    urn=urn,
                    name=_asset_name(entity, urn),
                    owner=_first_owner(entity.get("ownership")),
                )
            )
        return assets

    def get_asset(self, urn: str) -> AssetMeta | None:
        data = self._run(_ASSET_QUERY, variables={"urn": urn})
        ds = _dig(data, "dataset")
        return _dataset_to_meta(ds, urn) if ds else None

    def get_assets(self, urns: list[str]) -> dict[str, AssetMeta]:
        """Fetch many assets in a single GraphQL round-trip (aliased queries).

        Avoids the N-calls cost of looping ``get_asset`` — e.g. when listing the
        whole monitored watchlist. Unknown URNs are simply absent from the map;
        a failed request degrades to an empty map rather than raising.
        """
        if not urns:
            return {}
        aliases = {f"a{i}": urn for i, urn in enumerate(urns)}
        query = _batch_asset_query(list(aliases))
        variables = {alias: urn for alias, urn in aliases.items()}
        try:
            data = self._run(query, variables=variables) or {}
        except Exception as exc:  # noqa: BLE001 — best-effort bulk read
            logger.warning("batch get_assets failed (%d urns): %s", len(urns), exc)
            return {}
        out: dict[str, AssetMeta] = {}
        for alias, urn in aliases.items():
            ds = data.get(alias)
            if ds:
                out[urn] = _dataset_to_meta(ds, urn)
        return out

    def get_lineage(self, urn: str) -> Lineage:
        data = self._run(_LINEAGE_QUERY, variables={"urn": urn})
        ds = _dig(data, "dataset") or {}
        return Lineage(
            upstream=_lineage_nodes(ds.get("upstream")),
            downstream=_lineage_nodes(ds.get("downstream")),
        )

    # --- protocol methods (write-back) ---------------------------------------
    def tag_asset(self, urn: str, tag: str) -> str | None:
        """Create the tag (idempotent) and attach it to the asset.

        Returns the tag URN, or ``None`` if the write failed. This is what makes
        a detected issue visible on the asset's page in the DataHub UI.
        """
        from datahub.configuration.common import GraphError
        from datahub.emitter.mce_builder import make_tag_urn

        g = self._graph()
        try:
            tag_urn = g.create_tag(tag)
        except GraphError:
            # Already exists (or create not permitted) — the URN is deterministic.
            tag_urn = make_tag_urn(tag)
        try:
            g.execute_graphql(
                _ADD_TAGS_MUTATION, variables={"tagUrn": tag_urn, "resourceUrn": urn}
            )
        except GraphError as exc:
            logger.warning("Failed to attach tag %s to %s: %s", tag_urn, urn, exc)
            return None
        return tag_urn

    def assert_issue(
        self,
        urn: str,
        *,
        issue_type: str,
        severity: str,
        description: str,
        field_path: str | None = None,
    ) -> str | None:
        """Register a custom assertion on the asset and report a FAILURE result.

        Returns the assertion URN, or ``None`` on failure. Surfaces the issue in
        the asset's Validation tab as a first-class DataHub assertion.
        """
        from datahub.configuration.common import GraphError
        from datahub.emitter.mce_builder import make_assertion_urn

        g = self._graph()
        # Deterministic URN so re-scanning the same asset+issue updates one
        # assertion in place instead of minting a duplicate each run.
        stable_urn = make_assertion_urn(_assertion_id(urn, issue_type))
        try:
            res = g.upsert_custom_assertion(
                urn=stable_urn,
                entity_urn=urn,
                type=issue_type,
                description=description,
                field_path=field_path,
                platform_name="dataco",  # required: the tool that ran the check
            )
            returned = res.get("urn") if isinstance(res, dict) else None
            assertion_urn = returned or stable_urn
            # A freshly-upserted assertion is eventually consistent — reporting a
            # result can 500 with "does not exist" for a moment. Retry briefly.
            for attempt in range(5):
                try:
                    g.execute_graphql(
                        _REPORT_RESULT_MUTATION,
                        variables={
                            "urn": assertion_urn,
                            "ts": int(time.time() * 1000),
                            "type": "FAILURE",
                            "props": [
                                {
                                    "key": "severity",
                                    "value": _assertion_severity(severity),
                                }
                            ],
                        },
                    )
                    break
                except GraphError as exc:
                    if _is_transient_report_error(exc) and attempt < 4:
                        time.sleep(2)
                        continue
                    raise
            return assertion_urn
        except GraphError as exc:
            logger.warning("Failed to assert issue on %s: %s", urn, exc)
            return None


# --- defensive parsing helpers -----------------------------------------------


def _is_not_found(exc: Exception) -> bool:
    # Match acryl-datahub's GraphError by class name so this module needs no
    # SDK import at call time (keeps the offline mapping tests SDK-free).
    if type(exc).__name__ != "GraphError":
        return False
    msg = str(exc).lower()
    return "failed to find entity" in msg or "bad_request" in msg


def _is_transient_report_error(exc: Exception) -> bool:
    """A ``reportAssertionResult`` failure a brief retry may clear.

    Right after upsert the assertion is eventually consistent, and if the search
    backend (OpenSearch) is still warming up GMS returns a 500 whose wording
    varies: "does not exist", "Failed to retrieve entity", "Search query failed",
    "Try again". Retry on any of these; surface everything else immediately.
    """
    msg = str(exc).lower()
    return any(
        s in msg
        for s in (
            "does not exist",
            "failed to retrieve entity",
            "search query failed",
            "try again",
        )
    )


def _assertion_severity(severity: str) -> str:
    """Map Dataco severity to DataHub's assertion severity (LOW/MEDIUM/HIGH)."""
    s = (severity or "").lower()
    if s in ("critical", "high"):
        return "HIGH"
    if s == "medium":
        return "MEDIUM"
    return "LOW"


def _assertion_id(entity_urn: str, issue_type: str) -> str:
    """Deterministic assertion id for an asset+issue_type, so write-back is
    idempotent (re-runs upsert the same assertion instead of duplicating)."""
    digest = hashlib.sha1(f"dataco|{entity_urn}|{issue_type}".encode()).hexdigest()
    return f"dataco-{digest[:24]}"


def _batch_asset_query(aliases: list[str]) -> str:
    """One query fetching many datasets, each under its own alias."""
    decl = ", ".join(f"${a}: String!" for a in aliases)
    body = "\n".join(
        f"  {a}: dataset(urn: ${a}) {{ {_DATASET_FIELDS} }}" for a in aliases
    )
    return f"query batch({decl}) {{\n{body}\n}}"


def _dataset_to_meta(ds: dict, urn: str) -> AssetMeta:
    """Map a GraphQL ``dataset`` node to our ``AssetMeta`` domain type."""
    props = ds.get("properties") or {}
    editable = ds.get("editableProperties") or {}
    fields = [
        Field(name=f.get("fieldPath", ""), type=f.get("nativeDataType", ""))
        for f in _dig(ds, "schemaMetadata", "fields") or []
    ]
    return AssetMeta(
        urn=urn,
        name=_asset_name(ds, urn),
        description=props.get("description") or editable.get("description") or "",
        owner=_first_owner(ds.get("ownership")),
        schema_fields=fields,
        freshness=None,  # TODO: map dataset freshness once validated on live schema
        tags=_tag_names(ds.get("tags")),
    )


def _dig(obj: Any, *keys: str) -> Any:
    """Walk nested dict keys, returning None on any miss."""
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _asset_name(entity: dict, urn: str) -> str:
    props = entity.get("properties") or {}
    info = entity.get("info") or {}
    name = props.get("name") or entity.get("name") or info.get("name")
    if name:
        return name
    raw = entity.get("jobId") or entity.get("flowId")
    return _unqualify(raw) if raw else _name_from_urn(urn)


def _unqualify(value: str) -> str:
    # b2fd91.foo -> foo (datapack namespace prefixes); keep email-like ids
    if "@" in value:
        return value
    return value.rsplit(".", 1)[-1]


def _name_from_urn(urn: str) -> str:
    # urn:li:dataset:(platform,DB.SCHEMA.table,ENV) -> table
    if urn.startswith("urn:li:dataset:"):
        parts = urn.rsplit(",", 2)
        if len(parts) >= 2:
            return parts[-2].rsplit(".", 1)[-1]
    # other types: last comma/colon segment, closing paren stripped
    # (urn:li:dataJob:(flowUrn,jobId) -> jobId, urn:li:corpuser:jdoe -> jdoe)
    seg = urn.rsplit(",", 1)[-1].rstrip(")")
    seg = seg.rsplit(":", 1)[-1]
    return _unqualify(seg)


def _readable_urn_id(urn: str) -> str:
    # urn:li:corpuser:jdoe -> jdoe ; urn:li:tag:pii -> pii
    return urn.rsplit(":", 1)[-1]


def _first_owner(ownership: Any) -> str | None:
    for entry in _dig(ownership, "owners") or []:
        owner_urn = _dig(entry, "owner", "urn")
        if owner_urn:
            return _readable_urn_id(owner_urn)
    return None


def _tag_names(tags: Any) -> list[str]:
    out: list[str] = []
    for entry in _dig(tags, "tags") or []:
        tag_urn = _dig(entry, "tag", "urn")
        if tag_urn:
            out.append(_readable_urn_id(tag_urn))
    return out


def _lineage_nodes(result: Any) -> list[AssetNode]:
    nodes: list[AssetNode] = []
    for rel in _dig(result, "relationships") or []:
        entity = rel.get("entity") or {}
        urn = entity.get("urn")
        if urn:
            nodes.append(AssetNode(urn=urn, name=_asset_name(entity, urn)))
    return nodes
