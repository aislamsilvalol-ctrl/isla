"""ISLA V2 — labels, explainability, provenance and demo isolation.

All deterministic: no network, no keys, in-memory/tmp SQLite only.
"""
from isla.engine import LABELS, score_label, top_topics, why_trending


def test_label_ladder_covers_full_range():
    assert score_label(0) == "QUIET"
    assert score_label(19) == "QUIET"
    assert score_label(20) == "MOVING"
    assert score_label(45) == "EMERGING"
    assert score_label(60) == "ACCELERATING"
    assert score_label(75) == "BREAKOUT"
    assert score_label(90) == "VIRAL"
    assert score_label(100) == "VIRAL"


def test_labels_are_ordered_and_complete():
    assert LABELS == ["QUIET", "MOVING", "EMERGING", "ACCELERATING",
                      "BREAKOUT", "VIRAL"]


def test_why_never_empty_and_never_invents():
    # zero data → honest "collecting baseline", not a made-up factor
    why = why_trending({})
    assert len(why) == 1
    assert "collecting baseline" in why[0]


def test_why_lists_only_observable_factors():
    why = why_trending({
        "velocity_pct": 120.0, "acceleration_pct": 40.0, "jerk_pct": 10.0,
        "sources": ["hackernews", "bluesky"], "anomaly": 55,
        "regional_lead": True, "regions": ["BR"], "source_baseline_x": 3.2,
    })
    joined = " | ".join(why)
    assert "+120%" in joined                # velocity is the measured number
    assert "2 independent sources" in joined
    assert "anomaly" in joined
    assert "3.2x above" in joined
    assert "absent in home region" in joined


def test_demo_data_is_simulated_and_isolated(tmp_path):
    from isla.cli import _seed_demo
    from isla.store import Event, open_db

    db_path = str(tmp_path / "demo.db")
    _seed_demo(db_path)
    db = open_db(db_path)
    rows = top_topics(db, limit=10)
    assert rows, "demo must produce live topics"
    # every demo topic is flagged — the UI banner depends on this
    assert all(r["simulated"] for r in rows)
    # every demo event carries the simulated mark for provenance
    events = db.query(Event).all()
    assert events and all(e.simulated == 1 for e in events)


def test_demo_breakout_curve_actually_breaks_out(tmp_path):
    from isla.cli import _seed_demo
    from isla.store import open_db

    db_path = str(tmp_path / "demo2.db")
    _seed_demo(db_path)
    db = open_db(db_path)
    rows = {r["topic"]: r for r in top_topics(db, limit=10)}
    rising = rows["demo: synthwave revival"]
    fading = rows["demo: fading meme"]
    assert rising["opportunity"] > fading["opportunity"]
    assert (rising["velocity_pct"] or 0) > 0
    assert (fading["velocity_pct"] or 0) < 0


def test_series_history_feeds_sparkline(tmp_path):
    from isla.cli import _seed_demo
    from isla.store import open_db

    db_path = str(tmp_path / "demo3.db")
    _seed_demo(db_path)
    db = open_db(db_path)
    rows = top_topics(db, limit=10)
    assert all(isinstance(r["series"], list) for r in rows)
    assert any(len(r["series"]) >= 1 for r in rows)
