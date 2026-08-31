"""SOURCE ADAPTERS — the heart of ISLA's extensibility (Source SDK).

Every source is a plain function returning normalized signals:
    {"source": str, "topic_raw": str, "engagement": float, "url": str,
     "category": str, "region": str (optional)}

Rules (non-negotiable):
- declare honest freshness ("~15m RSS"), never fake "real-time";
- a source that fails NEVER takes the scan down;
- engagement is a REAL number from the source, or an operator-set weight
  (RSS) — never invented;
- official/public APIs only.

See docs/SOURCE_SDK.md to add your own.
"""
import re
import time

import httpx

from .config import Config

UA = {"User-Agent": "isla-radar/0.1 (open-source)"}


# ---------------------------------------------------------------- keyless
def fetch_google_trends(cfg: Config) -> list[dict]:
    """Official per-country trending RSS — the search engine itself."""
    out = []
    for geo in cfg.trends_geos[:5]:
        r = httpx.get(f"https://trends.google.com/trending/rss?geo={geo}",
                      headers={"User-Agent": "Mozilla/5.0 (isla)"},
                      timeout=15, follow_redirects=True)
        r.raise_for_status()
        for raw in r.text.split("<item>")[1:][:20]:
            title = re.search(r"<title>(.*?)</title>", raw)
            traffic = re.search(r"<ht:approx_traffic>(.*?)</ht:approx_traffic>", raw)
            link = re.search(r"<ht:news_item_url>(.*?)</ht:news_item_url>", raw)
            if not title:
                continue
            t = int(re.sub(r"\D", "", traffic.group(1)) or 0) if traffic else 0
            out.append({"source": "google_trends",
                        "topic_raw": title.group(1).strip(),
                        "engagement": float(max(t, 1)),
                        "url": link.group(1).strip() if link else "",
                        "category": "search", "region": geo})
    return out


WIKI_SKIP = ("especial:", "special:", "wikipédia:", "wikipedia:", "main_page",
             "página_principal", "ficheiro:", "file:", "ajuda:", "help:")


def fetch_wikipedia(cfg: Config) -> list[dict]:
    """Yesterday's top pageviews — what the world is actually researching."""
    from datetime import datetime, timedelta, timezone

    day = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    out = []
    for lang in cfg.wiki_langs[:3]:
        r = httpx.get(
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
            f"{lang}.wikipedia/all-access/{day.year}/{day.month:02d}/{day.day:02d}",
            headers=UA, timeout=15)
        r.raise_for_status()
        for a in r.json().get("items", [{}])[0].get("articles", [])[:40]:
            name = a.get("article", "")
            if any(name.lower().startswith(p) for p in WIKI_SKIP):
                continue
            out.append({"source": "wikipedia",
                        "topic_raw": name.replace("_", " "),
                        "engagement": float(a.get("views", 0)),
                        "url": f"https://{lang}.wikipedia.org/wiki/{name}",
                        "category": "knowledge",
                        "region": cfg.home_region if lang == "pt" else "GLOBAL"})
    return out


def fetch_bluesky(cfg: Config) -> list[dict]:
    """Public trends endpoint — real postCount, real startedAt, no key."""
    r = httpx.get("https://public.api.bsky.app/xrpc/app.bsky.unspecced.getTrends",
                  params={"limit": 25}, headers=UA, timeout=15)
    r.raise_for_status()
    out = []
    for t in r.json().get("trends", []):
        posts = float(t.get("postCount", 0))
        name = t.get("displayName") or ""
        if name and posts > 0:
            out.append({"source": "bluesky", "topic_raw": name,
                        "engagement": posts,
                        "url": "https://bsky.app" + (t.get("link") or ""),
                        "category": t.get("category") or "social"})
    return out


def fetch_rss(cfg: Config) -> list[dict]:
    """Operator-added RSS/Atom feeds (news of any outlet, any country)."""
    out = []
    for url in cfg.rss_feeds[:20]:
        try:
            r = httpx.get(url, headers=UA, timeout=12, follow_redirects=True)
            r.raise_for_status()
        except Exception:
            continue  # one bad feed never kills the scan
        for m in re.finditer(r"<item>(.*?)</item>", r.text, re.S):
            raw = m.group(1)
            title = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>",
                              raw, re.S)
            link = re.search(r"<link>(.*?)</link>", raw)
            if title:
                out.append({"source": "rss",
                            "topic_raw": title.group(1).strip()[:200],
                            "engagement": 1.0,  # weight, not fake metric
                            "url": (link.group(1).strip() if link else url),
                            "category": "news"})
        out = out[:120]
    return out


# ---------------------------------------------------------------- keyed
def fetch_youtube(cfg: Config) -> list[dict]:
    """mostPopular via plain API key (no OAuth needed)."""
    out = []
    for cat in (None, "20"):
        params = {"part": "snippet,statistics", "chart": "mostPopular",
                  "regionCode": cfg.home_region, "maxResults": 25,
                  "key": cfg.youtube_api_key}
        if cat:
            params["videoCategoryId"] = cat
        r = httpx.get("https://www.googleapis.com/youtube/v3/videos",
                      params=params, timeout=15)
        r.raise_for_status()
        for item in r.json().get("items", []):
            out.append({"source": "youtube",
                        "topic_raw": item["snippet"]["title"],
                        "engagement": float(item.get("statistics", {})
                                            .get("viewCount", 0)),
                        "url": f"https://youtube.com/watch?v={item['id']}",
                        "category": "gaming" if cat == "20" else "video"})
    return out


_tw = {"token": None, "exp": 0.0}


def fetch_twitch(cfg: Config) -> list[dict]:
    if not _tw["token"] or time.time() > _tw["exp"] - 60:
        r = httpx.post("https://id.twitch.tv/oauth2/token", data={
            "client_id": cfg.twitch_client_id,
            "client_secret": cfg.twitch_client_secret,
            "grant_type": "client_credentials"}, timeout=15)
        r.raise_for_status()
        d = r.json()
        _tw["token"] = d["access_token"]
        _tw["exp"] = time.time() + float(d.get("expires_in", 3600))
    r = httpx.get("https://api.twitch.tv/helix/streams?first=50",
                  headers={"Client-Id": cfg.twitch_client_id,
                           "Authorization": f"Bearer {_tw['token']}"},
                  timeout=15)
    r.raise_for_status()
    games: dict[str, float] = {}
    out = []
    for s in r.json().get("data", []):
        v = float(s.get("viewer_count", 0))
        g = s.get("game_name", "")
        if g:
            games[g] = games.get(g, 0) + v
        if v >= 15000:
            out.append({"source": "twitch", "topic_raw": s.get("user_name", ""),
                        "engagement": v,
                        "url": f"https://twitch.tv/{s.get('user_login', '')}",
                        "category": "streamer"})
    for g, v in games.items():
        out.append({"source": "twitch", "topic_raw": g, "engagement": v,
                    "url": "https://twitch.tv/directory", "category": "gaming"})
    return out


_rd = {"token": None, "exp": 0.0}


def fetch_reddit(cfg: Config) -> list[dict]:
    if not _rd["token"] or time.time() > _rd["exp"] - 60:
        r = httpx.post("https://www.reddit.com/api/v1/access_token",
                       auth=(cfg.reddit_client_id, cfg.reddit_client_secret),
                       data={"grant_type": "client_credentials"},
                       headers={"User-Agent": "isla:radar:v0.1"}, timeout=15)
        r.raise_for_status()
        d = r.json()
        _rd["token"] = d["access_token"]
        _rd["exp"] = time.time() + float(d.get("expires_in", 3600))
    out = []
    for sub in cfg.subreddits[:6]:
        r = httpx.get(f"https://oauth.reddit.com/r/{sub}/rising?limit=30",
                      headers={"User-Agent": "isla:radar:v0.1",
                               "Authorization": f"Bearer {_rd['token']}"},
                      timeout=15)
        r.raise_for_status()
        for child in r.json().get("data", {}).get("children", []):
            d = child.get("data", {})
            if d.get("stickied") or d.get("over_18"):
                continue
            out.append({"source": "reddit", "topic_raw": d.get("title", ""),
                        "engagement": float(d.get("score", 0))
                        + 2.0 * d.get("num_comments", 0),
                        "url": f"https://reddit.com{d.get('permalink', '')}",
                        "category": sub})
    return out




def fetch_hackernews(cfg: Config) -> list[dict]:
    """Official HN Algolia API — front page, real points+comments, no key."""
    r = httpx.get("https://hn.algolia.com/api/v1/search",
                  params={"tags": "front_page", "hitsPerPage": 30},
                  headers=UA, timeout=15)
    r.raise_for_status()
    out = []
    for h in r.json().get("hits", []):
        title = h.get("title") or ""
        if not title:
            continue
        out.append({"source": "hackernews", "topic_raw": title,
                    "engagement": float(h.get("points", 0))
                    + 2.0 * float(h.get("num_comments", 0)),
                    "url": h.get("url")
                    or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    "category": "tech", "author": h.get("author", "")})
    return out


# each adapter declares capabilities + HONEST freshness (Source SDK)
SOURCES: dict[str, dict] = {
    "google_trends": {"fetch": fetch_google_trends,
                      "configured": lambda c: True,
                      "freshness": "~15m (official RSS, per country)"},
    "wikipedia": {"fetch": fetch_wikipedia, "configured": lambda c: True,
                  "freshness": "daily (yesterday's top — confirmation)"},
    "bluesky": {"fetch": fetch_bluesky, "configured": lambda c: True,
                "freshness": "live trends (real postCount)"},
    "hackernews": {"fetch": fetch_hackernews, "configured": lambda c: True,
                   "freshness": "front page (official Algolia API)"},
    "rss": {"fetch": fetch_rss,
            "configured": lambda c: bool(c.rss_feeds),
            "freshness": "each feed's cadence — set ISLA_RSS_FEEDS"},
    "youtube": {"fetch": fetch_youtube,
                "configured": lambda c: bool(c.youtube_api_key),
                "freshness": "~10m (Data API) — set ISLA_YOUTUBE_API_KEY"},
    "twitch": {"fetch": fetch_twitch,
               "configured": lambda c: bool(c.twitch_client_id
                                            and c.twitch_client_secret),
               "freshness": "live viewers (Helix) — set ISLA_TWITCH_*"},
    "reddit": {"fetch": fetch_reddit,
               "configured": lambda c: bool(c.reddit_client_id
                                            and c.reddit_client_secret),
               "freshness": "near real-time rising — set ISLA_REDDIT_*"},
}
