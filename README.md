# ISLA

**Open-source virality radar.** Signals in → trends out — measured between
real samples, never invented.

ISLA watches public sources (search, encyclopedic attention, social trends,
live streams, communities, any RSS feed) and answers one question before
everyone else: **what is about to go viral?**

It is the virality-tracking engine born inside [USINA]. Extracted here as a
standalone, self-hostable tool.

## Honesty rules (non-negotiable)

- **No invented virality.** Velocity = Δengagement between real samples.
  Without 2 samples ISLA says `collecting baseline`, never a made-up number.
- **No fake real-time.** Every source declares its true freshness
  (`~15m RSS`, `daily`, `live`).
- **Acceleration beats size.** A small topic accelerating outranks a huge
  saturated one.
- **Official/public APIs only.** BYOK — bring your own keys; none required
  to start.

## Quick start

```
pip install -e .
isla scan       # sweep all configured sources (3 work with ZERO keys)
isla top        # live topics ranked by opportunity
isla sources    # source health / what each key unlocks
```

Works out of the box with **Google Trends (per country), Wikipedia pageviews
and Bluesky trends — no API keys**. Add keys in `.env` to unlock YouTube,
Twitch, Reddit and any RSS feed (see `.env.example`).

Optional: `ANTHROPIC_API_KEY` upgrades topic clustering with an LLM;
without it a deterministic heuristic does the job.

## What you get per topic

```
[ 87] gta 6                      BREAKOUT     +148%  LEAD:US
      velocity, acceleration, jerk, lifecycle, source diversity,
      anomaly vs own baseline, confidence (LOW/MED/HIGH), regional lead
```

`LEAD:US` = strong abroad, absent in your home region — your early window.

## JSON API

```
pip install -e '.[serve]'
isla serve --port 8800
# GET /topics?sort=opportunity   GET /sources   POST /scan
```

## Build your own source

Every source is a small adapter returning normalized signals. See
[docs/SOURCE_SDK.md](docs/SOURCE_SDK.md) — ~20 lines gets you a new source.

## License

[MIT](LICENSE) — use it, fork it, build on it. If you ship something with
ISLA inside, a link back is appreciated (not required).
