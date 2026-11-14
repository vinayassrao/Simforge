"""Database tables: episodes, their events and their evaluations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class EpisodeRecord(Base):
    __tablename__ = "episodes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    scenario_name: Mapped[str] = mapped_column(String(120))
    agent_mode: Mapped[str] = mapped_column(String(16), index=True)
    seed: Mapped[int]
    status: Mapped[str] = mapped_column(String(16), index=True, default="created")
    created_at: Mapped[datetime] = mapped_column(default=utc_now, index=True)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    steps: Mapped[int] = mapped_column(default=0)
    progress: Mapped[int] = mapped_column(default=0)
    collisions: Mapped[int] = mapped_column(default=0)
    invalid_actions: Mapped[int] = mapped_column(default=0)
    elapsed_seconds: Mapped[float] = mapped_column(default=0.0)
    score: Mapped[float | None] = mapped_column(default=None)
    success: Mapped[bool | None] = mapped_column(default=None)
    failure_reason: Mapped[str | None] = mapped_column(String(64), default=None)
    trajectory: Mapped[list[Any]] = mapped_column(JSON, default=list)
    incidents: Mapped[list[Any]] = mapped_column(JSON, default=list)

    events: Mapped[list[EventRecord]] = relationship(
        back_populates="episode", cascade="all, delete-orphan", order_by="EventRecord.seq"
    )
    evaluation: Mapped[EvaluationRecord | None] = relationship(
        back_populates="episode", cascade="all, delete-orphan", uselist=False
    )


class EventRecord(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_episode_seq", "episode_id", "seq"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"))
    seq: Mapped[int]
    step: Mapped[int]
    type: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(16), index=True)
    description: Mapped[str] = mapped_column(String(400))
    entity_id: Mapped[str | None] = mapped_column(String(64), default=None)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[str] = mapped_column(String(40))

    episode: Mapped[EpisodeRecord] = relationship(back_populates="events")


class EvaluationRecord(Base):
    __tablename__ = "evaluations"

    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), primary_key=True)
    score: Mapped[float]
    success: Mapped[bool]
    report: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    episode: Mapped[EpisodeRecord] = relationship(back_populates="evaluation")
