import hashlib

from app.domain.types import Field, SchemaDiff


def schema_hash(fields: list[Field]) -> str:
    sorted_fields = sorted(fields, key=lambda f: (f.name, f.type))
    raw = ";".join(f"{f.name}:{f.type}" for f in sorted_fields)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def diff_schema(before: list[Field], after: list[Field]) -> SchemaDiff:
    before_map = {f.name: f.type for f in before}
    after_map = {f.name: f.type for f in after}

    before_names = set(before_map.keys())
    after_names = set(after_map.keys())

    added = sorted(after_names - before_names)
    removed = sorted(before_names - after_names)

    type_changed: list[tuple[str, str, str]] = []
    for name in before_names & after_names:
        if before_map[name] != after_map[name]:
            type_changed.append((name, before_map[name], after_map[name]))

    return SchemaDiff(added=added, removed=removed, type_changed=sorted(type_changed))
