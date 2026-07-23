from typing import Protocol


class Explanation:
    def __init__(
        self,
        summary: str,
        likely_cause: str,
        impacted_assets: list[str],
        confidence: str,
        recommended_action: str,
    ):
        self.summary = summary
        self.likely_cause = likely_cause
        self.impacted_assets = impacted_assets
        self.confidence = confidence
        self.recommended_action = recommended_action


class Brief:
    def __init__(
        self,
        subject: str,
        what_happened: str,
        what_is_affected: list[str],
        who_to_contact: str,
        next_step: str,
        estimated_impact: str,
    ):
        self.subject = subject
        self.what_happened = what_happened
        self.what_is_affected = what_is_affected
        self.who_to_contact = who_to_contact
        self.next_step = next_step
        self.estimated_impact = estimated_impact


class LLMClient(Protocol):
    def explain(self, context: dict) -> Explanation: ...

    def brief(self, context: dict) -> Brief: ...


def create_llm_client(provider: str | None = None) -> LLMClient:
    """Factory: build the configured LLMClient implementation.

    Resolution order:
      - ``provider`` argument, else ``LLM_PROVIDER`` env (default "anthropic").
      - "anthropic" / "openai": the corresponding client — but only if that
        provider's API key is available. With no credentials it falls back to
        the deterministic stub so the app and the demo still run offline.
      - "stub" / "fake" / "none": the deterministic stub.

    The provider SDKs (``anthropic`` / ``openai``) are imported lazily inside
    their branch, so importing this module never requires either SDK to be
    installed. ``LLM_MODEL`` overrides the provider default when set.
    """
    from app.config import (
        ANTHROPIC_API_KEY,
        ANTHROPIC_DEFAULT_MODEL,
        LLM_MODEL,
        LLM_PROVIDER,
        OPENAI_API_KEY,
        OPENAI_DEFAULT_MODEL,
    )

    name = (provider or LLM_PROVIDER or "anthropic").lower()

    if name in ("stub", "fake", "none"):
        return _stub_client()

    if name == "anthropic":
        if not ANTHROPIC_API_KEY:
            return _stub_client()
        from app.integrations.llm_anthropic import AnthropicLLMClient

        return AnthropicLLMClient(model=LLM_MODEL or ANTHROPIC_DEFAULT_MODEL)

    if name == "openai":
        if not OPENAI_API_KEY:
            return _stub_client()
        from app.integrations.llm_openai import OpenAILLMClient

        return OpenAILLMClient(model=LLM_MODEL or OPENAI_DEFAULT_MODEL)

    raise ValueError(
        f"Unknown LLM_PROVIDER: {name!r} (expected 'anthropic', 'openai', or 'stub')"
    )


def _stub_client() -> LLMClient:
    from tests.fakes import StubLLMClient

    return StubLLMClient()
