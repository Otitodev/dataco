from dataclasses import dataclass

from app.domain.types import Confidence


@dataclass
class ConfidenceContext:
    owner_present: bool = False
    lineage_complete: bool = False


def confidence_label(context: ConfidenceContext) -> str:
    if context.owner_present and context.lineage_complete:
        return Confidence.HIGH.value
    if context.owner_present or context.lineage_complete:
        return Confidence.MEDIUM.value
    return Confidence.LOW.value
