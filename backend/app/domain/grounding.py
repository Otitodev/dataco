"""Grounding guard — the runtime safety net behind the 'no hallucination'
promise. Filters a model's asset references down to only those that actually
appear in the retrieved context, so an invented asset name never reaches the UI.
"""

from collections.abc import Iterable


def ground_assets(candidates: Iterable[str], allowed: Iterable[str]) -> list[str]:
    """Keep only candidates whose name appears in ``allowed``.

    Case-insensitive and whitespace-tolerant; preserves the candidates' order
    and de-duplicates. Empty/blank names are dropped.
    """
    allowed_norm = {a.strip().lower() for a in allowed if a and a.strip()}
    out: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        key = (c or "").strip().lower()
        if key and key in allowed_norm and key not in seen:
            seen.add(key)
            out.append(c)
    return out
