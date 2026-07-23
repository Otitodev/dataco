from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(Enum):
    FRESHNESS_STALE = "freshness_stale"
    SCHEMA_DRIFT = "schema_drift"
    OWNER_MISSING = "owner_missing"
    OWNER_CHANGED = "owner_changed"


class IssueStatus(Enum):
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


class Confidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Field:
    name: str
    type: str


@dataclass
class SchemaDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    type_changed: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return bool(self.added or self.removed or self.type_changed)


@dataclass
class AssetNode:
    urn: str
    name: str


@dataclass
class Lineage:
    upstream: list[AssetNode] = field(default_factory=list)
    downstream: list[AssetNode] = field(default_factory=list)


@dataclass
class AssetMeta:
    urn: str
    name: str
    description: str = ""
    owner: str | None = None
    schema_fields: list[Field] = field(default_factory=list)
    freshness: str | None = None
    tags: list[str] = field(default_factory=list)
    docs: str | None = None


@dataclass
class MonitoringState:
    asset_id: str
    last_checked_at: datetime | None = None
    freshness_status: str | None = None
    last_schema_hash: str = ""
    last_owner: str | None = None
    consecutive_failures: int = 0
