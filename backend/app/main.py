from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    assets,
    dashboard,
    issues,
    monitoring,
    reasoning,
    scan,
    search,
)
from app.config import SCAN_INTERVAL_SECONDS
from app.services import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Opt-in autonomous loop: only runs when SCAN_INTERVAL_SECONDS > 0, so tests
    # (which build create_app() per fixture) and offline runs stay loop-free.
    scheduler.start(SCAN_INTERVAL_SECONDS)
    try:
        yield
    finally:
        await scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="Dataco", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:4173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(dashboard.router)
    app.include_router(issues.router)
    app.include_router(assets.router)
    app.include_router(reasoning.router)
    app.include_router(scan.router)
    app.include_router(monitoring.router)
    app.include_router(search.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
