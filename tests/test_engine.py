"""ISLA — deterministic engine tests (no network, no keys)."""
from datetime import datetime, timedelta, timezone

from isla.engine import lifecycle, normalize, opportunity_score


def utcnow():
    return datetime.now(timezone.utc)


def test_normalize_strips_noise():
    assert normalize("O GTA 6 foi ADIADO!!! (reação)") == "gta adiado reação"


def test_no_velocity_means_emerging_never_invented():
    assert lifecycle(None, None, utcnow()) == "EMERGING"


def test_breakout_needs_velocity_and_acceleration():
    assert lifecycle(80.0, 20.0, utcnow()) == "BREAKOUT"
    assert lifecycle(80.0, -5.0, utcnow()) != "BREAKOUT"


def test_dead_after_12h_silence():
    assert lifecycle(50.0, 10.0, utcnow() - timedelta(hours=13)) == "DEAD"


def test_acceleration_beats_size():
    small_fast = {"velocity_pct": 120, "acceleration_pct": 60,
                  "freshness": 90, "source_diversity": 50, "anomaly": 40,
                  "cross_platform": True, "engagement": 500}
    big_flat = {"velocity_pct": 2, "acceleration_pct": 0, "freshness": 10,
                "source_diversity": 25, "anomaly": 0,
                "cross_platform": False, "engagement": 9_000_000}
    assert opportunity_score(small_fast) > opportunity_score(big_flat)


def test_regional_lead_bonus_capped():
    sc = {"velocity_pct": 200, "acceleration_pct": 100, "freshness": 100,
          "source_diversity": 100, "anomaly": 100, "cross_platform": True,
          "regional_lead": True}
    assert opportunity_score(sc) <= 100
