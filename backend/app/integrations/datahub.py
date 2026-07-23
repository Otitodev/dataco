from typing import Protocol

from app.domain.types import AssetMeta, Lineage


class DataHubClient(Protocol):
    # --- read ---------------------------------------------------------------
    def search(self, query: str) -> list[AssetMeta]: ...

    def get_asset(self, urn: str) -> AssetMeta | None: ...

    def get_lineage(self, urn: str) -> Lineage: ...

    # --- write-back (closes the loop: results go back into DataHub) ----------
    def tag_asset(self, urn: str, tag: str) -> str | None: ...

    def assert_issue(
        self,
        urn: str,
        *,
        issue_type: str,
        severity: str,
        description: str,
        field_path: str | None = None,
    ) -> str | None: ...


def create_datahub_client(provider: str | None = None) -> DataHubClient:
    """Factory: build the configured DataHubClient implementation.

    Resolution order:
      - ``provider`` argument, else ``DATAHUB_PROVIDER`` env (default "datahub").
      - "datahub": a live DataHub client via GraphQL — but only if a
        ``DATAHUB_TOKEN`` is set. With no token it falls back to the seeded
        ``FakeDataHubClient`` so the app and the demo run offline.
      - "fake" / "stub" / "none": the seeded fake.

    The ``acryl-datahub`` SDK is imported lazily inside ``DataHubGraphClient``,
    so importing this module never requires the SDK to be installed.
    """
    from app.config import DATAHUB_PROVIDER, DATAHUB_TOKEN, DATAHUB_URL

    name = (provider or DATAHUB_PROVIDER or "datahub").lower()

    if name in ("fake", "stub", "none"):
        return _fake_client()

    if name == "datahub":
        if not DATAHUB_TOKEN:
            return _fake_client()
        from app.integrations.datahub_graph import DataHubGraphClient

        return DataHubGraphClient(server=DATAHUB_URL, token=DATAHUB_TOKEN)

    raise ValueError(
        f"Unknown DATAHUB_PROVIDER: {name!r} (expected 'datahub' or 'fake')"
    )


def _fake_client() -> DataHubClient:
    from tests.fakes import DEMO_DATA, FakeDataHubClient

    return FakeDataHubClient(**DEMO_DATA)
