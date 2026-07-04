"""Build ZEQ/ZCQ/ZIQ from aggregated metrics (pure computation)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from .constants import ALGORITHM_VERSION, BASE_IMPACT, DEFAULT_WEIGHTS
from .core import (
    compute_a,
    compute_comm_index,
    compute_equity,
    compute_inspire_index,
    compute_s,
    compute_spd,
    compute_t,
    compute_zcq,
    compute_zeq,
    compute_ziq,
    compute_ziq_per_member,
    get_k,
    get_k_att,
    get_n_eff,
)
from .models import RealtimeZenqResult, ZcqInputs, ZeqInputs


@dataclass(slots=True)
class SponsorMetricsSnapshot:
    user_id: str
    session_mins: float = 0.0
    message_count: int = 0
    substantive_message_count: int = 0
    active_inspire: int = 0
    passive_inspire: int = 0
    avg_ras: float = 1.0
    streak_days: int = 0
    new_user: bool = False
    spark_active: bool = False
    target_status: str = "none"
    effort_weight: float = 0.0
    commitment_factor: float = 1.0


@dataclass(slots=True)
class SponsorZeqBreakdown:
    user_id: str
    zeq: float
    components: dict[str, float]
    weights: dict[str, float]


@dataclass(slots=True)
class StudentContextSnapshot:
    student_id: str
    zqa_composite: float = 0.0
    zqa_band: str = "1 - Beginning"
    baseline_zqa: Optional[float] = None
    spd: float = 1.0
    need_band: str = "developing"
    attendance_30d: float = 0.0


@dataclass(slots=True)
class CircleZenqComputation:
    circle_id: str
    circle_name: str
    algorithm_version: str
    zeq_avg: float
    zcq: float
    spd_avg: float
    ziq: float
    ziq_per_member: float
    sponsor_count: int
    student_count: int
    group_size: int
    sponsor_breakdowns: list[SponsorZeqBreakdown] = field(default_factory=list)
    student_contexts: list[StudentContextSnapshot] = field(default_factory=list)
    zcq_inputs: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


def compute_sponsor_zeq(
    metrics: SponsorMetricsSnapshot,
    *,
    effort_shares: list[float],
    weights: Optional[dict[str, float]] = None,
) -> SponsorZeqBreakdown:
    w = weights or DEFAULT_WEIGHTS
    t = compute_t(metrics.session_mins, metrics.avg_ras)
    a = compute_a(metrics.target_status)
    s = compute_s(
        metrics.streak_days,
        new_user=metrics.new_user,
        spark_active=metrics.spark_active,
    )
    comm = compute_comm_index(
        metrics.message_count,
        metrics.substantive_message_count,
        metrics.avg_ras,
    )
    inspire = compute_inspire_index(metrics.active_inspire, metrics.passive_inspire)
    equity = compute_equity(effort_shares)
    zeq = compute_zeq(
        t=t,
        a=a,
        s=s,
        comm_index=comm,
        inspire_index=inspire,
        equity=equity,
        commitment_factor=metrics.commitment_factor,
        weights=w,
    )
    return SponsorZeqBreakdown(
        user_id=metrics.user_id,
        zeq=round(zeq, 4),
        components={
            "T": round(t, 4),
            "A": round(a, 4),
            "S": round(s, 4),
            "Cm": round(comm, 4),
            "In": round(inspire, 4),
            "E": round(equity, 4),
            "C": round(metrics.commitment_factor, 4),
        },
        weights=dict(w),
    )


def aggregate_student_spd(students: list[StudentContextSnapshot]) -> float:
    if not students:
        return 1.0
    return round(sum(s.spd for s in students) / len(students), 4)


def build_zcq_inputs(
    *,
    need_band: str,
    attendance_30d_ratio: float,
    group_size: int,
    absent_today: bool = False,
) -> ZcqInputs:
    return ZcqInputs(
        need_band=need_band,
        attendance_30d_ratio=attendance_30d_ratio,
        absent_today=absent_today,
        group_size=max(1, group_size),
    )


def compute_zcq_from_inputs(inputs: ZcqInputs) -> tuple[float, dict[str, float]]:
    k = get_k(inputs.need_band)
    k_att = get_k_att(inputs.attendance_30d_ratio, inputs.absent_today)
    n_eff = get_n_eff(inputs.group_size)
    zcq = compute_zcq(k=k, k_att=k_att, n_eff=n_eff)
    return round(zcq, 4), {
        "K": round(k, 4),
        "K_att": round(k_att, 4),
        "N_eff": round(n_eff, 4),
    }


def compute_circle_zenq(
    *,
    circle_id: str,
    circle_name: str,
    sponsor_metrics: list[SponsorMetricsSnapshot],
    students: list[StudentContextSnapshot],
    weights: Optional[dict[str, float]] = None,
) -> CircleZenqComputation:
    sponsor_count = len(sponsor_metrics)
    student_count = len(students)
    group_size = max(1, sponsor_count + student_count)

    effort_total = sum(max(0.0, m.effort_weight) for m in sponsor_metrics) or float(sponsor_count or 1)
    effort_shares = [
        (max(0.0, m.effort_weight) / effort_total) if effort_total else 0.0
        for m in sponsor_metrics
    ]

    breakdowns = [
        compute_sponsor_zeq(m, effort_shares=effort_shares, weights=weights)
        for m in sponsor_metrics
    ]

    if breakdowns:
        zeq_avg = round(
            sum(b.zeq * share for b, share in zip(breakdowns, effort_shares))
            / (sum(effort_shares) or 1.0),
            4,
        )
    else:
        zeq_avg = 0.0

    spd_avg = aggregate_student_spd(students)

    if students:
        need_band = max(students, key=lambda s: _need_rank(s.need_band)).need_band
        attendance_ratio = sum(s.attendance_30d for s in students) / len(students) / 100.0
    else:
        need_band = "standard"
        attendance_ratio = 0.0

    zcq_inputs = build_zcq_inputs(
        need_band=need_band,
        attendance_30d_ratio=attendance_ratio,
        group_size=group_size,
    )
    zcq, zcq_parts = compute_zcq_from_inputs(zcq_inputs)

    ziq = round(compute_ziq(zeq=zeq_avg, zcq=zcq, spd=spd_avg), 2)
    n_eff = get_n_eff(group_size)
    ziq_per_member = round(compute_ziq_per_member(ziq=ziq, n_eff=n_eff), 2)

    return CircleZenqComputation(
        circle_id=circle_id,
        circle_name=circle_name,
        algorithm_version=ALGORITHM_VERSION,
        zeq_avg=zeq_avg,
        zcq=zcq,
        spd_avg=spd_avg,
        ziq=ziq,
        ziq_per_member=ziq_per_member,
        sponsor_count=sponsor_count,
        student_count=student_count,
        group_size=group_size,
        sponsor_breakdowns=breakdowns,
        student_contexts=students,
        zcq_inputs={
            "need_band": need_band,
            "attendance_30d_ratio": round(attendance_ratio, 4),
            "group_size": group_size,
            **zcq_parts,
        },
        summary={
            "formula": "ZIQ = BASE × ZEQ × ZCQ × SPD",
            "base_impact": BASE_IMPACT,
        },
    )


def to_realtime_result(computation: CircleZenqComputation) -> RealtimeZenqResult:
    avg_zqa = 0.0
    if computation.student_contexts:
        avg_zqa = sum(s.zqa_composite for s in computation.student_contexts) / len(
            computation.student_contexts
        )
    band = computation.student_contexts[0].zqa_band if computation.student_contexts else "1 - Beginning"
    return RealtimeZenqResult(
        zqa_composite=round(avg_zqa, 2),
        zqa_band=band,
        spd=computation.spd_avg,
        ziq=computation.ziq,
        ziq_per_member=computation.ziq_per_member,
    )


def computation_to_dict(computation: CircleZenqComputation) -> dict[str, Any]:
    return {
        "circle_id": computation.circle_id,
        "circle_name": computation.circle_name,
        "algorithm_version": computation.algorithm_version,
        "zeq_avg": computation.zeq_avg,
        "zcq": computation.zcq,
        "spd_avg": computation.spd_avg,
        "ziq": computation.ziq,
        "ziq_per_member": computation.ziq_per_member,
        "sponsor_count": computation.sponsor_count,
        "student_count": computation.student_count,
        "group_size": computation.group_size,
        "zcq_inputs": computation.zcq_inputs,
        "summary": computation.summary,
        "sponsors": [
            {
                "user_id": b.user_id,
                "zeq": b.zeq,
                "components": b.components,
                "weights": b.weights,
            }
            for b in computation.sponsor_breakdowns
        ],
        "students": [asdict(s) for s in computation.student_contexts],
    }


def _need_rank(band: str) -> int:
    return {
        "standard": 0,
        "developing": 1,
        "high": 2,
        "critical": 3,
    }.get((band or "").lower(), 1)


def student_spd_from_zqa(baseline: Optional[float], current: float) -> float:
    return round(compute_spd(baseline, current), 4)
