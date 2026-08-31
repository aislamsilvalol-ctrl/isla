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
    # série p/ sparkline (últimos 30 pontos reais)
    series_hist = list(prev.get("series", []))[-29:]
    if series:
        series_hist.append(round(series[0], 1))
    topic.scores = {
        "series": series_hist,
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
        # honest labeling: a demo topic stays SIMULATED across recomputes
        "simulated": bool(prev.get("simulated")),
    }


# ISLA VIRALITY SCORE → label (thresholds calibráveis por env)
import os as _os

_TH = [int(x) for x in _os.environ.get(
    "ISLA_SCORE_THRESHOLDS", "20,40,60,75,90").split(",")]
LABELS = ["QUIET", "MOVING", "EMERGING", "ACCELERATING", "BREAKOUT", "VIRAL"]


def score_label(score: int) -> str:
    for i, th in enumerate(_TH):
        if score < th:
            return LABELS[i]
    return LABELS[-1]


def why_trending(sc: dict) -> list[str]:
    """EXPLICABILIDADE (V2 item 15): fatores observáveis, nunca score mágico."""
    out = []
    if sc.get("velocity_pct") is not None:
        out.append(f"engagement velocity {sc['velocity_pct']:+.0f}% between real samples")
    if (sc.get("acceleration_pct") or 0) > 0:
        out.append(f"acceleration {sc['acceleration_pct']:+.0f}%")
    if (sc.get("jerk_pct") or 0) > 0:
        out.append(f"acceleration itself rising ({sc['jerk_pct']:+.0f}%)")
    srcs = sc.get("sources") or []
    if len(srcs) > 1:
        out.append(f"confirmed across {len(srcs)} independent sources ({', '.join(srcs)})")
    if sc.get("anomaly", 0) > 30:
        out.append(f"anomaly vs own baseline: {sc['anomaly']}/100")
    if sc.get("regional_lead"):
        out.append(f"strong in {'/'.join(sc.get('regions', []))}, absent in home region")
    if sc.get("source_baseline_x"):
        out.append(f"{sc['source_baseline_x']}x above the source's typical signal")
    if not out:
        out.append("collecting baseline — needs 2+ samples before any claim")
    return out


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

    # BASELINE NORMALIZATION (item 27): sinal típico por fonte nesta varredura
    src_totals: dict[str, list[float]] = {}
    for s2 in deduped:
        src_totals.setdefault(s2["source"], []).append(s2["engagement"])
    src_median = {k: sorted(v)[len(v) // 2] for k, v in src_totals.items() if v}

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
        base = src_median.get(source) or 1.0
        db.add(Sample(topic_id=topic.id, source=source,
                      engagement=a["engagement"], items=a["items"],
                      meta={"regions": sorted(a["regions"]),
                            "baseline_x": round(a["engagement"] / base, 1)}))
        touched[topic.id] = topic
    db.commit()
    # PROVENANCE (item 30): cada sinal relevante vira Event rastreável
    from .store import Event

    name_to_id = {t.canonical: t.id for t in touched.values()}
    for s2 in deduped:
        canonical = mapping.get(s2["topic_raw"], "")
        tid = name_to_id.get(canonical)
        if tid and s2["engagement"] >= 1:
            db.add(Event(topic_id=tid, source=s2["source"],
                         title=s2["topic_raw"][:300], url=s2["url"][:600],
                         engagement=s2["engagement"],
                         region=s2.get("region", "")[:16]))
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
        score = opportunity_score(sc)
        out.append({"id": t.id, "topic": t.canonical, "lifecycle": t.lifecycle,
                    "opportunity": score, "label": score_label(score),
                    "series": sc.get("series", []), "why": why_trending(sc),
                    "url": t.best_url,
                    "simulated": bool(sc.get("simulated")),
                    **{k: sc.get(k) for k in
                       ("velocity_pct", "acceleration_pct", "confidence",
                        "sources", "regions", "regional_lead", "engagement")}})
    keys = {"opportunity": lambda x: x["opportunity"],
            "rising": lambda x: x["velocity_pct"] or -999,
            "engagement": lambda x: x["engagement"] or 0}
    out.sort(key=keys.get(sort, keys["opportunity"]), reverse=True)
    return out[:limit]
