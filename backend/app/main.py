from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assets, dashboard, issues, reasoning, scan, search


def create_app() -> FastAPI:
    app = FastAPI(title="Dataco", version="0.1.0")

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
    app.include_router(search.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
