"""SQLite storage — self-contained, zero external services."""
from datetime import datetime, timezone

from sqlalchemy import (JSON, DateTime, Float, Integer, String, create_engine,
                        select)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(32), default="")
    lifecycle: Mapped[str] = mapped_column(String(16), default="EMERGING")
    scores: Mapped[dict] = mapped_column(JSON, default=dict)
    best_url: Mapped[str] = mapped_column(String(600), default="")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                default=utcnow, index=True)


class Sample(Base):
    __tablename__ = "samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(Integer, index=True)
    source: Mapped[str] = mapped_column(String(24))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                         default=utcnow, index=True)
    engagement: Mapped[float] = mapped_column(Float, default=0)
    items: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class Event(Base):
    """Raw normalized signal — DATA PROVENANCE (V2 item 30): every number
    on screen traces back to a source URL and timestamp."""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(Integer, index=True)
    source: Mapped[str] = mapped_column(String(24), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                         default=utcnow, index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    url: Mapped[str] = mapped_column(String(600), default="")
    engagement: Mapped[float] = mapped_column(Float, default=0)
    region: Mapped[str] = mapped_column(String(16), default="")
    language: Mapped[str] = mapped_column(String(8), default="")
    simulated: Mapped[int] = mapped_column(Integer, default=0)  # NUNCA misturar


def open_db(path: str) -> Session:
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    return Session(engine)


def recent_samples(db: Session, topic_id: int, limit: int = 8) -> list[Sample]:
    return list(db.execute(
        select(Sample).where(Sample.topic_id == topic_id)
        .order_by(Sample.ts.desc()).limit(limit)).scalars())
