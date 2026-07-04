"""ZenQ engine persistence models (Phase 0 — admin observatory)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ZenqEvent(Base):
    __tablename__ = "zenq_events"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    circle_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, unique=True)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)


class ZenqSponsorMetrics(Base):
    __tablename__ = "zenq_sponsor_metrics"
    __table_args__ = (
        UniqueConstraint("circle_id", "user_id", "window_key", name="uq_zenq_sponsor_metrics_window"),
        {"schema": "ZENK"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    window_key: Mapped[str] = mapped_column(String(16), nullable=False, default="30d")
    session_mins: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    substantive_message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_inspire: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passive_inspire: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_ras: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_status: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    effort_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    commitment_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    spark_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metrics_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)


class ZenqStudentContext(Base):
    __tablename__ = "zenq_student_context"
    __table_args__ = (
        UniqueConstraint("student_id", name="uq_zenq_student_context_student"),
        {"schema": "ZENK"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    circle_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    zqa_composite: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zqa_band: Mapped[str] = mapped_column(String(50), nullable=False, default="1 - Beginning")
    baseline_zqa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spd: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    need_band: Mapped[str] = mapped_column(String(20), nullable=False, default="developing")
    attendance_30d: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    spark_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    context_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)


class ZenqSponsorScore(Base):
    __tablename__ = "zenq_sponsor_scores"
    __table_args__ = (
        UniqueConstraint("circle_id", "user_id", name="uq_zenq_sponsor_scores_member"),
        {"schema": "ZENK"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    zeq: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    components_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)


class ZenqCircleScore(Base):
    __tablename__ = "zenq_circle_scores"
    __table_args__ = {"schema": "ZENK"}

    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    circle_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    zeq_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zcq: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    spd_avg: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    ziq: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ziq_raw: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ziq_per_member: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    decay_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    sponsor_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    student_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0-phase0")
    summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)


class ZenqComputationSnapshot(Base):
    __tablename__ = "zenq_computation_snapshots"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    circle_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(64), nullable=False, default="materializer")
    inputs_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    outputs_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)


class ZenqTargetLog(Base):
    __tablename__ = "zenq_target_logs"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    sponsor_user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    quarter: Mapped[str] = mapped_column(String(10), nullable=False, default="Q1")
    fy: Mapped[str] = mapped_column(String(20), nullable=False, default="2025-26")
    target_status: Mapped[str] = mapped_column(String(16), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logged_by_user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)


class ZenqSparkEvent(Base):
    __tablename__ = "zenq_spark_events"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)


class ZenqWelfareCase(Base):
    __tablename__ = "zenq_welfare_cases"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    student_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    sponsor_user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    signals_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class ZenqWeightConfig(Base):
    __tablename__ = "zenq_weight_config"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    weights_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    analysis_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    proposed_by: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    approved_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
