"""The set of live DataHub assets the scan agent watches.

Populated with URNs from the showcase-ecommerce pack loaded on the demo
DataHub instance. ``seed_live.py`` primes a ``MonitoringState`` baseline for
each so the first ``POST /scan`` deterministically detects an issue; if this
list is empty it falls back to discovering assets via ``DISCOVERY_QUERIES``.

Confirm/extend these against the live instance with ``GET /search?q=...``.
"""

# Known real URNs on the demo instance (b2fd91.* namespace).
WATCHLIST: list[str] = [
    "urn:li:dataset:(urn:li:dataPlatform:looker,"
    "b2fd91.order-entry.explore.order_details,PROD)",
]

# Fallback: if WATCHLIST is empty, seed_live discovers assets with these terms.
DISCOVERY_QUERIES: list[str] = ["order", "customer", "product"]

# How many discovered assets to prime when falling back to discovery.
DISCOVERY_LIMIT = 3
