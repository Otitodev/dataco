import pytest

import app.config as config
from app.integrations.datahub import create_datahub_client


@pytest.fixture(autouse=True)
def clear_datahub_config(monkeypatch):
    """Start every test from a known, credential-free config."""
    monkeypatch.setattr(config, "DATAHUB_TOKEN", "")
    monkeypatch.setattr(config, "DATAHUB_URL", "http://localhost:8080")
    monkeypatch.setattr(config, "DATAHUB_PROVIDER", "datahub")


def test_falls_back_to_fake_when_no_token():
    # "datahub" is the default provider, but with no token the factory must not
    # try to reach a live instance — it returns the seeded fake.
    from tests.fakes import FakeDataHubClient

    client = create_datahub_client()
    assert isinstance(client, FakeDataHubClient)
    # ...and it carries the demo data so the app works offline.
    assert client.get_asset("urn:dataco:lab_ingestion_feed") is not None


def test_explicit_fake_provider():
    from tests.fakes import FakeDataHubClient

    assert isinstance(create_datahub_client("fake"), FakeDataHubClient)


def test_datahub_selected_when_token_present(monkeypatch):
    monkeypatch.setattr(config, "DATAHUB_TOKEN", "dh-test-token")
    from app.integrations.datahub_graph import DataHubGraphClient

    client = create_datahub_client("datahub")
    assert isinstance(client, DataHubGraphClient)
    assert client._server == "http://localhost:8080"
    # Constructed without the acryl-datahub SDK — the SDK is only imported on
    # the first live call, so construction stays offline-safe.


def test_datahub_provider_env_drives_selection(monkeypatch):
    monkeypatch.setattr(config, "DATAHUB_PROVIDER", "fake")
    from tests.fakes import FakeDataHubClient

    # No explicit argument — the factory reads DATAHUB_PROVIDER.
    assert isinstance(create_datahub_client(), FakeDataHubClient)


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown DATAHUB_PROVIDER"):
        create_datahub_client("collibra")
