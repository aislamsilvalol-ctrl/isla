# ISLA Source SDK — build a source in ~20 lines

Every source is a function in `isla/sources.py` (or your fork) that returns
normalized signals:

```python
def fetch_my_source(cfg: Config) -> list[dict]:
    return [{
        "source": "my_source",        # unique name
        "topic_raw": "item title",    # goes to the clusterer
        "engagement": 123.0,          # REAL number from the source
        "url": "https://…",           # canonical (dedup key)
        "category": "gaming",         # optional
        "region": "BR",               # optional (feeds regional lead)
    }]
```

Register it with capabilities and an HONEST freshness label:

```python
SOURCES["my_source"] = {
    "fetch": fetch_my_source,
    "configured": lambda cfg: bool(cfg.my_source_key),  # or True if keyless
    "freshness": "the REAL cadence — never write 'real-time' unless it is",
}
```

## Rules

1. **One source down never kills the scan** — the runner wraps every fetch.
2. **Engagement is real** — a number the source reports, or an explicit
   operator weight (like RSS). Never invented.
3. **Freshness is honest** — declare the true delay.
4. **Official/public APIs only** — no scraping behind logins, no ToS abuse.
5. Fail with a clear error string; ISLA shows it in `isla sources`.
