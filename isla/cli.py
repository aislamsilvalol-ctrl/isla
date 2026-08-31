"""ISLA CLI — git clone → configure → run."""
import argparse
import json
import sys

from .config import load
from .engine import scan, top_topics
from .sources import SOURCES
from .store import open_db


def main() -> int:
    p = argparse.ArgumentParser(
        prog="isla",
        description="ISLA — open-source virality radar. "
                    "Signals in, trends out — measured, never invented.")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("scan", help="run one full sweep of all configured sources")
    top = sub.add_parser("top", help="show live topics")
    top.add_argument("--sort", default="opportunity",
                     choices=["opportunity", "rising", "engagement"])
    top.add_argument("--limit", type=int, default=15)
    top.add_argument("--json", action="store_true")
    sub.add_parser("sources", help="show source health/configuration")
    serve = sub.add_parser("serve", help="start the web UI + API (needs [serve])")
    serve.add_argument("--port", type=int, default=8800)
    sub.add_parser("replay", help="recompute all metrics from stored samples "
                                  "(no network — deterministic re-run)")
    demo = sub.add_parser("demo", help="seed a SEPARATE demo db with SIMULATED "
                                       "data, clearly labeled — never mixed "
                                       "with real signals")
    demo.add_argument("--db", default="isla-demo.db")
    args = p.parse_args()

    cfg = load()
    if args.cmd == "demo":
        _seed_demo(args.db)
        return 0
    db = open_db(cfg.db_path)

    if args.cmd == "scan":
        r = scan(db, cfg)
        print(f"scan: {r['signals']} signals → {r['topics']} topics")
        for name, h in r["health"].items():
            extra = f" — {h.get('items', 0)} signals" if h.get("items") else ""
            err = f" ({h.get('error')})" if h.get("error") else ""
            print(f"  {name}: {h['status']}{extra}{err}")
        return 0
    if args.cmd == "top":
        rows = top_topics(db, limit=args.limit, sort=args.sort)
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
            return 0
        if not rows:
            print("no live topics — run `isla scan` first "
                  "(velocity needs 2+ samples)")
            return 0
        for i, t in enumerate(rows, 1):
            v = (f"{t['velocity_pct']:+.0f}%" if t["velocity_pct"] is not None
                 else "collecting baseline")
            lead = f" LEAD:{'/'.join(t['regions'])}" if t.get("regional_lead") else ""
            print(f"{i:2d}. [{t['opportunity']:3d}] {t['topic'][:50]:50s} "
                  f"{t['lifecycle']:12s} {v}{lead}")
        return 0
    if args.cmd == "sources":
        for name, src in SOURCES.items():
            ok = src["configured"](cfg)
            print(f"  {name:14s} {'configured' if ok else 'off':10s} "
                  f"{src['freshness']}")
        return 0
    if args.cmd == "replay":
        from .engine import update_metrics
        from .store import Topic
        from sqlalchemy import select as _select

        topics = db.execute(_select(Topic)).scalars().all()
        for t in topics:
            update_metrics(db, t, cfg.home_region)
        db.commit()
        print(f"replay: recomputed metrics for {len(topics)} topics "
              "from stored samples (zero network calls)")
        for i, t in enumerate(top_topics(db, limit=10), 1):
            print(f"{i:2d}. [{t['opportunity']:3d}] {t['label']:13s} "
                  f"{t['topic'][:50]}")
        return 0
    if args.cmd == "serve":
        try:
            import uvicorn

            from .api import build_app
        except ImportError:
            print("install extras: pip install 'isla[serve]'")
            return 1
        uvicorn.run(build_app(), host="0.0.0.0", port=args.port)
        return 0
    p.print_help()
    return 0


def _seed_demo(db_path: str) -> None:
    """SIMULATED fixtures in a SEPARATE db (V2 item 36): explore the product
    without keys or network. Every topic is flagged simulated → amber banner
    in the UI, SIM tag on provenance. Real and demo data never share a file."""
    from datetime import timedelta

    from .engine import update_metrics
    from .store import Event, Sample, Topic, open_db, utcnow

    db = open_db(db_path)
    now = utcnow()
    fixtures = [  # (topic, engagement curve oldest→newest = one shape each)
        ("demo: synthwave revival", [40, 55, 90, 170]),      # breakout
        ("demo: quiet cooking hack", [80, 82, 85, 84]),      # flat
        ("demo: indie game jam", [10, 30, 45, 50]),          # decelerating rise
        ("demo: fading meme", [200, 150, 90, 60]),           # declining
    ]
    for name, curve in fixtures:
        t = Topic(canonical=name, category="demo",
                  first_seen=now - timedelta(minutes=len(curve) * 5))
        db.add(t)
        db.flush()
        for i, eng in enumerate(curve):
            ts = now - timedelta(minutes=(len(curve) - 1 - i) * 5)
            db.add(Sample(topic_id=t.id, source="demo", ts=ts,
                          engagement=eng, items=3,
                          meta={"regions": ["BR"], "baseline_x": 1.0}))
            db.add(Event(topic_id=t.id, source="demo", ts=ts,
                         title=f"{name} — simulated signal {i + 1}",
                         url="https://example.com/simulated",
                         engagement=eng, region="BR", simulated=1))
        db.commit()
        update_metrics(db, t, "BR")
        t.scores = {**t.scores, "simulated": True}
        db.commit()
    print(f"demo: seeded {len(fixtures)} SIMULATED topics into {db_path}")
    print("      run:  ISLA_DB=" + db_path + " isla serve")
    print("      the UI will show the SIMULATED DATA banner — demo data is")
    print("      never written to your real database.")


if __name__ == "__main__":
    sys.exit(main())
