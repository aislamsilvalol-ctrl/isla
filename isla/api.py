"""Minimal JSON API — `isla serve` (optional extra)."""
from fastapi import FastAPI

from .config import load
from .engine import scan, top_topics
from .sources import SOURCES
from .store import open_db


def build_app() -> FastAPI:
    app = FastAPI(title="ISLA", version="0.1.0",
                  description="Open-source virality radar")
    cfg = load()

    @app.get("/topics")
    def topics(sort: str = "opportunity", limit: int = 20):
        db = open_db(cfg.db_path)
        try:
            return top_topics(db, limit=limit, sort=sort)
        finally:
            db.close()

    @app.post("/scan")
    def run_scan():
        db = open_db(cfg.db_path)
        try:
            return scan(db, cfg)
        finally:
            db.close()

    @app.get("/sources")
    def sources():
        return {name: {"configured": s["configured"](cfg),
                       "freshness": s["freshness"]}
                for name, s in SOURCES.items()}

    return app
