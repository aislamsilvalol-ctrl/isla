# ISLA architecture

One process, one file of state. Deliberately.

```
 ┌────────────────────────────────────────────────────────────┐
 │                       isla serve                           │
 │                                                            │
 │  asyncio scan loop (ISLA_SCAN_INTERVAL, default 300s)      │
 │        │                                                   │
 │        ▼                                                   │
 │  SOURCES registry ──► fetch each configured connector      │
 │  (google_trends, wikipedia, bluesky, hackernews,           │
 │   rss*, youtube*, twitch*, reddit*)      *BYOK             │
 │        │  normalized signals {topic_raw, engagement,       │
 │        │   url, region, source}                            │
 │        ▼                                                   │
 │  TREND ENGINE                                              │
 │   dedup → cluster (heuristic, LLM optional) →              │
 │   per-source baseline → Samples + Events (provenance) →    │
 │   velocity/accel/jerk/lifecycle/anomaly/regional-lead →    │
 │   opportunity score → label QUIET…VIRAL → why-factors      │
 │        │                                                   │
 │        ▼                                                   │
 │  SQLite (topics, samples, events)                          │
 │        │                                                   │
 │        ├──► REST /api/v1/* (trends, emerging, sources,     │
 │        │        stats, health)                             │
 │        └──► SSE /api/v1/stream ──► web UI reacts live      │
 └────────────────────────────────────────────────────────────┘
```

## Data model

- **Topic** — canonical cluster (`gta 6`), lifecycle, scores JSON
  (series history, velocity, confidence, regions…).
- **Sample** — one (topic, source, tick) aggregate. The unit velocity is
  measured between. Carries `baseline_x` (engagement ÷ source median this
  sweep) so a niche source's spike isn't drowned by YouTube-scale numbers.
- **Event** — one raw signal, kept for **provenance**: title, URL, region,
  engagement, timestamp, and a `simulated` flag that is `1` only for demo
  fixtures — which live in a separate database file anyway.

## Honest measurement

Velocity is Δengagement between two *real* samples of the same topic.
One sample → `collecting baseline`. Lifecycle needs velocity + acceleration.
The opportunity score weights velocity, acceleration, freshness, source
diversity, anomaly-vs-own-baseline and cross-platform confirmation; labels
(`QUIET → VIRAL`) are plain threshold cuts over that score, calibratable via
`ISLA_SCORE_THRESHOLDS`. `why_trending()` lists only observable factors —
if there is nothing to observe, it says so.

## Why no infra zoo (design decision, not a limitation)

ISLA's working set is small: hundreds of live topics, thousands of samples
per day. At that scale:

- **SQLite** beats a database server — zero setup, one file, transactional,
  and `git clone → isla scan` works on any machine in under a minute.
- **asyncio loop + SSE** beat Kafka/Redis — one producer (the scan loop),
  N cheap consumers (browser tabs). A queue would add operational surface
  and deliver the same messages later.
- **In-process fan-out** beats websocket brokers — listeners are asyncio
  queues; a dropped browser costs nothing.

### When you outgrow it (the documented path)

| Pressure | Move to |
|---|---|
| >1M events/day, multi-node scan | Kafka (or Redpanda) between connectors and engine |
| Heavy analytical queries over history | ClickHouse for `events`, keep SQLite/Postgres for live state |
| Many servers behind a load balancer | Postgres + LISTEN/NOTIFY (or Redis pub/sub) replacing in-process fan-out |
| Connector isolation / rate-limit pools | Split connectors into workers pushing to the queue |

Each swap is behind a seam that already exists: `SOURCES` registry (input),
`store.py` (persistence), `_notify()` (fan-out). Nothing else changes.
