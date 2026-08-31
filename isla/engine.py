"""TREND ENGINE — velocity, acceleration and lifecycle from REAL samples.

Principle: ask "what is ACCELERATING?" before "what is popular?".
Without two samples there is no velocity — ISLA says "collecting baseline"
instead of inventing a number. Optional LLM improves clustering; without a
key, the deterministic heuristic does the job.
"""
import re
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .config import Config
from .sources import SOURCES
from .store import Sample, Topic, recent_samples, utcnow

STOPWORDS = set("""a o os as de da do das dos e em no na nos nas um uma para
por com sem que foi vai tem ser está mais the an of in on for to and or is
are was be at by it this that with from has have will new""".split())


def normalize(title: str) -> str:
    t = re.sub(r"[^\w\sÀ-ÿ]", " ", title.lower())
    words = [w for w in t.split() if w not in STOPWORDS and len(w) > 2]
    return " ".join(words[:3]) or title[:40].lower()


def cluster(titles: list[str], cfg: Config) -> dict[str, str]:
    """title → canonical topic. Heuristic by default; LLM refines if key set."""
    mapping = {t: normalize(t) for t in titles}
    if cfg.anthropic_api_key and titles:
        try:
            import json as _json

            import anthropic

            client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
            listing = "\n".join(f"[{i}] {t[:140]}"
                                for i, t in enumerate(titles[:80]))
            msg = client.messages.create(
                model=cfg.llm_model, max_tokens=2000,
                system="Group titles into short canonical TOPICS (1-3 words, "
                       "the central entity/event). Reply ONLY JSON: "
                       '{"topics": [{"index": int, "topic": str}]}',
                messages=[{"role": "user", "content": listing}])
            text = "".join(b.text for b in msg.content if b.type == "text")
            data = _json.loads(re.sub(r"^[^{]*|[^}]*$", "", text))
            for e in data.get("topics", []):
                i = int(e.get("index", -1))
                if 0 <= i < len(titles) and e.get("topic"):
                    mapping[titles[i]] = str(e["topic"]).lower()[:80]
        except Exception:
            pass  # LLM optional: heuristic already covered everything
    return mapping


def lifecycle(velocity: float | None, accel: float | None,
              last_seen: datetime) -> str:
    now = utcnow()
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    if now - last_seen > timedelta(hours=12):
        return "DEAD"
    if now - last_seen > timedelta(hours=3):
        return "DECLINING"
    if velocity is None:
        return "EMERGING"
    if velocity > 40 and (accel or 0) > 0:
        return "BREAKOUT"
    if velocity > 10:
        return "ACCELERATING"
    if velocity < -20:
        return "DECLINING"
    return "SATURATED"


def update_metrics(db, topic: Topic, home_region: str) -> None:
    samples = recent_samples(db, topic.id)
    by_tick: dict[str, float] = {}
    sources: set[str] = set()
    regions: set[str] = set()
    for s in samples:
        key = s.ts.strftime("%Y%m%d%H%M")
        by_tick[key] = by_tick.get(key, 0) + s.engagement
        sources.add(s.source)
        for r in (s.meta or {}).get("regions", []):
            regions.add(r)
    series = [v for _, v in sorted(by_tick.items(), reverse=True)][:4]

    velocity = accel = jerk = None
    if len(series) >= 2 and series[1] > 0:
        velocity = round((series[0] - series[1]) / series[1] * 100, 1)
    if len(series) >= 3 and series[2] > 0:
        prev_v = (series[1] - series[2]) / series[2] * 100
        accel = round((velocity or 0) - prev_v, 1)
    if len(series) >= 4 and series[3] > 0:
        pv2 = (series[2] - series[3]) / series[3] * 100
        prev_a = ((series[1] - series[2]) / series[2] * 100 - pv2) \
            if series[2] > 0 else 0
        jerk = round((accel or 0) - prev_a, 1)

    fs = (topic.first_seen if topic.first_seen.tzinfo
          else topic.first_seen.replace(tzinfo=timezone.utc))
    age_min = (utcnow() - fs).total_seconds() / 60
    freshness = 100 if age_min <= 15 else max(0, int(100 * (1 - age_min / 1440)))
    anomaly = 0
    if len(series) >= 3:
        mid = sorted(series)[len(series) // 2]
        if mid > 0:
            anomaly = max(0, min(100, int((series[0] / mid - 1) * 50)))
    regional_lead = bool(regions and home_region not in regions
                         and any(r != "GLOBAL" for r in regions))

    topic.lifecycle = lifecycle(velocity, accel, topic.last_seen)
    prev = topic.scores or {}
    topic.scores = {
        "engagement": series[0] if series else 0,
        "velocity_pct": velocity, "acceleration_pct": accel, "jerk_pct": jerk,
        "samples": len(samples), "sources": sorted(sources),
        "source_diversity": min(100, len(sources) * 25),
        "cross_platform": len(sources) > 1,
        "confidence": ("LOW" if velocity is None else
                       "HIGH" if len(series) >= 4 and len(sources) >= 2
                       else "MEDIUM"),
        "anomaly": anomaly, "freshness": freshness,
        "regions": sorted(regions), "regional_lead": regional_lead,
        "first_sources": prev.get("first_sources") or sorted(sources),
    }


def opportunity_score(sc: dict) -> int:
    v = min(max(sc.get("velocity_pct") or 0, 0), 200) / 2
    a = min(max(sc.get("acceleration_pct") or 0, 0), 100)
    parts = [(v, 0.28), (a, 0.22), (sc.get("freshness", 0), 0.18),
             (sc.get("source_diversity", 25), 0.15),
             (sc.get("anomaly", 0), 0.12),
             (100 if sc.get("cross_platform") else 40, 0.05)]
    score = sum(val * w for val, w in parts)
    if sc.get("regional_lead"):
        score = min(100, score + 6)
    return int(round(score))


def scan(db, cfg: Config) -> dict:
    """One full sweep: fetch every configured source → cluster → measure."""
    signals: list[dict] = []
    health: dict[str, dict] = {}
    for name, src in SOURCES.items():
        if not src["configured"](cfg):
            health[name] = {"status": "unconfigured",
                            "freshness": src["freshness"]}
            continue
        t0 = time.monotonic()
        try:
            got = src["fetch"](cfg)
            signals.extend(got)
            health[name] = {"status": "ok", "items": len(got),
                            "latency_ms": int((time.monotonic() - t0) * 1000),
                            "freshness": src["freshness"]}
        except Exception as e:  # one source down never kills the scan
            health[name] = {"status": "error", "error": str(e)[:120],
                            "freshness": src["freshness"]}

    seen: set[str] = set()
    deduped = [s for s in signals
               if s["url"] not in seen and not seen.add(s["url"])]
    mapping = cluster([s["topic_raw"] for s in deduped], cfg)

    agg: dict[tuple[str, str], dict] = {}
    for s in deduped:
        key = (mapping.get(s["topic_raw"], s["topic_raw"][:40]), s["source"])
        a = agg.setdefault(key, {"engagement": 0.0, "items": 0,
                                 "url": s["url"], "best": -1.0,
                                 "category": s.get("category", ""),
                                 "regions": set()})
        a["engagement"] += s["engagement"]
        a["items"] += 1
        if s.get("region"):
            a["regions"].add(s["region"])
        if s["engagement"] > a["best"]:
            a["best"], a["url"] = s["engagement"], s["url"]

    touched: dict[int, Topic] = {}
    for (name, source), a in agg.items():
        topic = db.execute(select(Topic).where(
            Topic.canonical == name)).scalar_one_or_none()
        if topic is None:
            topic = Topic(canonical=name, category=a["category"])
            db.add(topic)
            db.flush()
        topic.last_seen = utcnow()
        if a["url"] and (not topic.best_url or "youtube" in a["url"]):
            topic.best_url = a["url"]
        db.add(Sample(topic_id=topic.id, source=source,
                      engagement=a["engagement"], items=a["items"],
                      meta={"regions": sorted(a["regions"])}))
        touched[topic.id] = topic
    db.commit()
    for topic in touched.values():
        update_metrics(db, topic, cfg.home_region)
    db.commit()
    return {"signals": len(deduped), "topics": len(touched), "health": health}


def top_topics(db, limit: int = 20, sort: str = "opportunity") -> list[dict]:
    rows = db.execute(select(Topic).where(
        Topic.last_seen >= utcnow() - timedelta(hours=24),
        Topic.lifecycle != "DEAD")).scalars().all()
    out = []
    for t in rows:
        sc = t.scores or {}
        out.append({"topic": t.canonical, "lifecycle": t.lifecycle,
                    "opportunity": opportunity_score(sc), "url": t.best_url,
                    **{k: sc.get(k) for k in
                       ("velocity_pct", "acceleration_pct", "confidence",
                        "sources", "regions", "regional_lead", "engagement")}})
    keys = {"opportunity": lambda x: x["opportunity"],
            "rising": lambda x: x["velocity_pct"] or -999,
            "engagement": lambda x: x["engagement"] or 0}
    out.sort(key=keys.get(sort, keys["opportunity"]), reverse=True)
    return out[:limit]
