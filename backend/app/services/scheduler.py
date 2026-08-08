"""The continuous scan scheduler — Dataco's autonomous heartbeat.

An in-process background loop that runs the scan agent over the watchlist every
``SCAN_INTERVAL_SECONDS``, so the agent *watches* the catalog instead of waiting
for a human to press "Scan now". Opt-in: the loop only starts when the interval
is > 0 (wired in ``app/main.py``'s lifespan), so CI, tests, and offline runs are
untouched by default.

The loop runs outside the request cycle, so it opens its own DB session per
cycle (never a ``Depends``) and drives the same ``scan_all`` service the REST
endpoint uses via ``resolve_urns`` — one code path, no drift.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from app.deps import SessionLocal, get_datahub, get_llm
from app.repository.store import Repository
from app.services.scan import resolve_urns, scan_all

logger = logging.getLogger(__name__)


@dataclass
class SchedulerState:
    enabled: bool = False
    interval_seconds: int = 0
    last_run_at: datetime | None = None
    last_scanned: int = 0
    last_detected: int = 0
    running: bool = False


_state = SchedulerState()
_task: asyncio.Task | None = None


def get_status() -> SchedulerState:
    return _state


def run_once() -> None:
    """One scan cycle over the resolved watchlist. Self-contained + safe.

    Opens and closes its own session so it never shares state across cycles.
    Wrapped so a transient failure (network blip, live-DataHub hiccup) logs and
    the loop lives on rather than dying.
    """
    db = SessionLocal()
    try:
        repo = Repository(db)
        urns = resolve_urns(repo)
        results = scan_all(
            urns, datahub=get_datahub(), repo=repo, llm=get_llm()
        )
        detected = sum(1 for r in results if r.detected)
        _state.last_run_at = datetime.now(UTC)
        _state.last_scanned = len(results)
        _state.last_detected = detected
        logger.info(
            "scheduled scan: %d asset(s), %d detected", len(results), detected
        )
    except Exception:  # noqa: BLE001 — the loop must survive any one bad cycle
        logger.exception("scheduled scan cycle failed")
    finally:
        db.close()


async def _loop(interval_seconds: int) -> None:
    # Run once on startup for instant feedback, then on the interval.
    await asyncio.to_thread(run_once)
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await asyncio.to_thread(run_once)
        except asyncio.CancelledError:
            break


def start(interval_seconds: int) -> None:
    """Start the background loop. No-op when interval_seconds <= 0."""
    global _task
    if interval_seconds <= 0 or _task is not None:
        return
    _state.enabled = True
    _state.interval_seconds = interval_seconds
    _state.running = True
    _task = asyncio.create_task(_loop(interval_seconds))
    logger.info("scan scheduler started (every %ds)", interval_seconds)


async def stop() -> None:
    """Cancel the background loop cleanly on shutdown."""
    global _task
    if _task is None:
        return
    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass
    _task = None
    _state.running = False
    logger.info("scan scheduler stopped")
