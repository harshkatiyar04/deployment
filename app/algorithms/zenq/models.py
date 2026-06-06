from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ZeqInputs:
    session_mins: float
    target_status: str
    streak_days: int
    new_user: bool
    spark_active: bool
    message_count: int
    substantive_message_count: int
    active_inspire: int
    passive_inspire: int
    avg_ras: float
    effort_shares: list[float]
    commitment_factor: float


@dataclass(slots=True)
class ZcqInputs:
    need_band: str
    attendance_30d_ratio: float
    absent_today: bool
    group_size: int


@dataclass(slots=True)
class ZqaInputs:
    language: Optional[float] = None
    maths: Optional[float] = None
    history: Optional[float] = None


@dataclass(slots=True)
class RealtimeZenqResult:
    zqa_composite: float
    zqa_band: str
    spd: float
    ziq: float
    ziq_per_member: float
