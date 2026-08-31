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
    serve = sub.add_parser("serve", help="start the JSON API (needs [serve])")
    serve.add_argument("--port", type=int, default=8800)
    args = p.parse_args()

    cfg = load()
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


if __name__ == "__main__":
    sys.exit(main())
