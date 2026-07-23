import pytest

import app.config as config
from app.integrations.llm import create_llm_client


@pytest.fixture(autouse=True)
def clear_credentials(monkeypatch):
    """Start every test from a known, credential-free config."""
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    monkeypatch.setattr(config, "LLM_MODEL", "")
    monkeypatch.setattr(config, "LLM_PROVIDER", "anthropic")


def test_falls_back_to_stub_when_no_credentials():
    # anthropic is the default provider, but with no key the factory must not
    # try to build a real client — it returns the deterministic stub.
    from tests.fakes import StubLLMClient

    assert isinstance(create_llm_client(), StubLLMClient)
    assert isinstance(create_llm_client("openai"), StubLLMClient)


def test_explicit_stub_provider():
    from tests.fakes import StubLLMClient

    monkeypatch_provider = create_llm_client("stub")
    assert isinstance(monkeypatch_provider, StubLLMClient)


def test_anthropic_selected_when_key_present(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-ant-test")
    from app.integrations.llm_anthropic import AnthropicLLMClient

    client = create_llm_client("anthropic")
    assert isinstance(client, AnthropicLLMClient)
    assert client._model == config.ANTHROPIC_DEFAULT_MODEL  # default model


def test_openai_selected_when_key_present(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-openai-test")
    from app.integrations.llm_openai import OpenAILLMClient

    client = create_llm_client("openai")
    assert isinstance(client, OpenAILLMClient)
    assert client._model == config.OPENAI_DEFAULT_MODEL  # default model


def test_llm_provider_env_drives_selection(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-openai-test")
    from app.integrations.llm_openai import OpenAILLMClient

    # No explicit provider argument — the factory reads LLM_PROVIDER.
    assert isinstance(create_llm_client(), OpenAILLMClient)


def test_llm_model_override_wins(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr(config, "LLM_MODEL", "claude-sonnet-5")

    client = create_llm_client("anthropic")
    assert client._model == "claude-sonnet-5"


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        create_llm_client("grok")
