from app.config import _clean


def test_clean_strips_whitespace():
    assert _clean("  gpt-5.6-luna  ") == "gpt-5.6-luna"


def test_clean_drops_misparsed_inline_comment():
    # python-dotenv can read `LLM_MODEL=   # note` as the comment text itself;
    # such a value must be treated as unset, not used as a model id.
    assert _clean("# optional override; blank -> provider default") == ""


def test_clean_handles_empty_and_none():
    assert _clean("") == ""
    assert _clean(None) == ""
