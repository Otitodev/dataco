import os


def _clean(value: str | None) -> str:
    """Trim whitespace and drop a mis-parsed inline comment.

    Some .env loaders (python-dotenv, used by ``uvicorn --env-file``) mis-read
    an *empty* line carrying a trailing comment — e.g. ``LLM_MODEL=   # note`` —
    as the comment text itself. Without this guard that stray comment would be
    used as a model id / provider name (→ OpenAI "invalid model ID").
    """
    value = (value or "").strip()
    return "" if value.startswith("#") else value


# DataHub metadata/lineage source (see app/integrations/datahub.py ->
# create_datahub_client). DATAHUB_URL points at the GMS API (port 8080),
# not the UI (port 9002).
DATAHUB_PROVIDER = os.getenv("DATAHUB_PROVIDER", "datahub")  # datahub | fake
DATAHUB_URL = os.getenv("DATAHUB_URL", "http://localhost:8080")
DATAHUB_TOKEN = os.getenv("DATAHUB_TOKEN", "")

# Write-back: when Dataco detects an issue it can push a tag + custom assertion
# back onto the affected asset in DataHub (Track 1 "close the loop"). Tags are
# namespaced under DATAHUB_TAG_PREFIX, e.g. "trust:schema_drift".
DATAHUB_WRITE_ENABLED = os.getenv("DATAHUB_WRITE_ENABLED", "true").lower() == "true"
DATAHUB_TAG_PREFIX = os.getenv("DATAHUB_TAG_PREFIX", "trust")

# LLM layer — provider-agnostic settings consumed by the LLM factory
# (app/integrations/llm.py -> create_llm_client).
LLM_PROVIDER = _clean(os.getenv("LLM_PROVIDER", "anthropic")) or "anthropic"
# Optional override; blank -> the selected provider's default model below.
LLM_MODEL = _clean(os.getenv("LLM_MODEL", ""))

# Anthropic (Claude)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_DEFAULT_MODEL = "claude-opus-4-8"

# OpenAI (GPT)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_DEFAULT_MODEL = _clean(os.getenv("OPENAI_MODEL", "")) or "gpt-4o"

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dataco.db")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
