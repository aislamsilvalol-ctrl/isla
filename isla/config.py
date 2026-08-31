"""BYOK configuration — everything from env, nothing hardcoded.

ISLA never ships with keys and never requires them: the keyless sources
(Google Trends, Wikipedia, Bluesky) work out of the box.
"""
import os
from dataclasses import dataclass, field


def _split(v: str) -> list[str]:
    return [x.strip() for x in v.split(",") if x.strip()]


@dataclass
class Config:
    db_path: str = os.environ.get("ISLA_DB", "isla.db")
    home_region: str = os.environ.get("ISLA_REGION", "BR")
    trends_geos: list[str] = field(
        default_factory=lambda: _split(os.environ.get("ISLA_TRENDS_GEOS", "BR,US")))
    wiki_langs: list[str] = field(
        default_factory=lambda: _split(os.environ.get("ISLA_WIKI_LANGS", "pt,en")))
    rss_feeds: list[str] = field(
        default_factory=lambda: _split(os.environ.get("ISLA_RSS_FEEDS", "")))
    # optional keys (each unlocks a source; absent = source stays off, honestly)
    youtube_api_key: str = os.environ.get("ISLA_YOUTUBE_API_KEY", "")
    twitch_client_id: str = os.environ.get("ISLA_TWITCH_CLIENT_ID", "")
    twitch_client_secret: str = os.environ.get("ISLA_TWITCH_CLIENT_SECRET", "")
    reddit_client_id: str = os.environ.get("ISLA_REDDIT_CLIENT_ID", "")
    reddit_client_secret: str = os.environ.get("ISLA_REDDIT_CLIENT_SECRET", "")
    subreddits: list[str] = field(
        default_factory=lambda: _split(os.environ.get("ISLA_SUBREDDITS",
                                                      "all,gaming")))
    # optional LLM (better clustering + trend→idea); heuristics without it
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    llm_model: str = os.environ.get("ISLA_LLM_MODEL", "claude-haiku-4-5-20251001")


def load() -> Config:
    return Config()
