"""ISLA V2 — public API (/api/v1), realtime SSE and the web UI.

- background scanner loop (ISLA_SCAN_INTERVAL seconds, default 300)
- SSE at /api/v1/stream: scan.completed + trend snapshots — real events only
- /system: connector health, events/min, latency — no fake numbers
- OpenAPI at /docs (FastAPI built-in)
"""
import asyncio
import json
import time
from datetime import timedelta

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import func, select

from .config import load
from .engine import scan, score_label, top_topics, why_trending
from .sources import SOURCES
from .store import Event, Sample, Topic, open_db, utcnow
from .ui import PAGE

_state: dict = {"last_scan": None, "last_result": None, "scan_ms": None,
                "listeners": set(), "scanning": False}


def _notify(payload: dict) -> None:
    for q in list(_state["listeners"]):
        try:
            q.put_nowait(payload)
        except Exception:
            _state["listeners"].discard(q)


async def _scan_loop(cfg, interval: int) -> None:
    while True:
        try:
            db = open_db(cfg.db_path)
            t0 = time.monotonic()
            _state["scanning"] = True
            result = await asyncio.to_thread(scan, db, cfg)
            _state["scan_ms"] = int((time.monotonic() - t0) * 1000)
            _state["last_scan"] = utcnow().isoformat()
            _state["last_result"] = result
            tops = top_topics(db, limit=30)
            db.close()
            _notify({"type": "scan.completed", "at": _state["last_scan"],
                     "signals": result["signals"], "topics": result["topics"],
                     "top": tops[:15]})
        except Exception as e:
            _notify({"type": "scan.error", "error": str(e)[:200]})
        finally:
            _state["scanning"] = False
        await asyncio.sleep(interval)


def build_app() -> FastAPI:
    import os

    cfg = load()
    interval = int(os.environ.get("ISLA_SCAN_INTERVAL", "300"))
    app = FastAPI(
        title="ISLA", version="0.2.0",
        description="Open-source virality radar — turns the public internet "
                    "into a live map of human attention. Real signals only.")

    @app.on_event("startup")
    async def _start():
        asyncio.create_task(_scan_loop(cfg, interval))

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home():
        return PAGE

    @app.get("/api/v1/trends")
    def trends(sort: str = "opportunity", limit: int = 40):
        db = open_db(cfg.db_path)
        try:
            return top_topics(db, limit=limit, sort=sort)
        finally:
            db.close()

    @app.get("/api/v1/trends/{topic_id}")
    def trend_detail(topic_id: int):
        db = open_db(cfg.db_path)
        try:
            t = db.get(Topic, topic_id)
            if t is None:
                return {"error": "not found"}
            sc = t.scores or {}
            events = db.execute(
                select(Event).where(Event.topic_id == topic_id)
                .order_by(Event.ts.desc()).limit(20)).scalars().all()
            return {
                "id": t.id, "topic": t.canonical, "lifecycle": t.lifecycle,
                "label": score_label(__import__(
                    "isla.engine", fromlist=["opportunity_score"]
                ).opportunity_score(sc)),
                "scores": sc, "why": why_trending(sc),
                "first_seen": t.first_seen.isoformat(),
                "provenance": [{"source": e.source, "title": e.title,
                                "url": e.url, "engagement": e.engagement,
                                "region": e.region, "ts": e.ts.isoformat(),
                                "simulated": bool(e.simulated)}
                               for e in events],
            }
        finally:
            db.close()

    @app.get("/api/v1/emerging")
    def emerging(limit: int = 20):
        """What might become viral NEXT: acceleration + anomaly + confirmation."""
        db = open_db(cfg.db_path)
        try:
            rows = top_topics(db, limit=200, sort="opportunity")
            rows.sort(key=lambda t: (
                (t.get("acceleration_pct") or 0)
                + (1 if len(t.get("sources") or []) > 1 else 0) * 20), reverse=True)
            return [r for r in rows
                    if (r.get("acceleration_pct") or 0) > 0][:limit]
        finally:
            db.close()

    @app.get("/api/v1/sources")
    def sources():
        health = (_state.get("last_result") or {}).get("health", {})
        return {name: {
            "configured": s["configured"](cfg),
            "freshness": s["freshness"],
            "state": ("MISCONFIGURED" if not s["configured"](cfg) else
                      "RATE_LIMITED" if "429" in str(
                          health.get(name, {}).get("error", "")) else
                      "OFFLINE" if health.get(name, {}).get("status") == "error"
                      else "HEALTHY" if health.get(name, {}).get("status") == "ok"
                      else "UNKNOWN"),
            **{k: v for k, v in health.get(name, {}).items()
               if k in ("items", "latency_ms", "error")},
        } for name, s in SOURCES.items()}

    @app.get("/api/v1/stats")
    def stats():
        db = open_db(cfg.db_path)
        try:
            hour_ago = utcnow() - timedelta(hours=1)
            events_hour = db.execute(select(func.count()).select_from(Event)
                                     .where(Event.ts >= hour_ago)).scalar_one()
            return {
                "topics_live": db.execute(
                    select(func.count()).select_from(Topic).where(
                        Topic.last_seen >= utcnow() - timedelta(hours=24),
                        Topic.lifecycle != "DEAD")).scalar_one(),
                "events_last_hour": events_hour,
                "events_per_min": round(events_hour / 60, 1),
                "samples_total": db.execute(
                    select(func.count()).select_from(Sample)).scalar_one(),
                "last_scan": _state["last_scan"],
                "last_scan_ms": _state["scan_ms"],
                "scan_interval_s": interval,
                "scanning_now": _state["scanning"],
                "realtime_listeners": len(_state["listeners"]),
            }
        finally:
            db.close()

    @app.get("/api/v1/health")
    def health():
        return {"ok": True, "version": "0.2.0"}

    @app.get("/api/v1/stream", include_in_schema=False)
    async def stream():
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        _state["listeners"].add(q)

        async def gen():
            try:
                yield f"data: {json.dumps({'type': 'hello', 'interval': interval})}\n\n"
                while True:
                    try:
                        item = await asyncio.wait_for(q.get(), timeout=25)
                        yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
            finally:
                _state["listeners"].discard(q)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache",
                                          "X-Accel-Buffering": "no"})

    return app
