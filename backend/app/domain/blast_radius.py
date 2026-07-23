from collections import deque

from app.domain.types import AssetNode, Lineage


def blast_radius(lineage: Lineage, root: AssetNode | None = None) -> list[AssetNode]:
    return list(lineage.downstream)


def critical_path(lineage: Lineage) -> list[AssetNode]:
    if not lineage.downstream:
        return []

    downstream = blast_radius(lineage)
    visited: set[str] = set()
    path: list[AssetNode] = []

    queue: deque[AssetNode] = deque(downstream)
    while queue:
        node = queue.popleft()
        if node.urn in visited:
            continue
        visited.add(node.urn)
        path.append(node)
        if len(lineage.downstream) > 0:
            queue.extend(lineage.downstream)

    return path[:5]
