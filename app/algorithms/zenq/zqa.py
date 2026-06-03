"""School-portal ZQA composite: academic + Bloom's + SEL with anti-gaming guards."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .constants import (
    ZQA_ACADEMIC_KEYS,
    ZQA_ACADEMIC_WEIGHTS,
    ZQA_ATTENDANCE_FLOOR_PCT,
    ZQA_BLOOMS_LEVEL_WEIGHTS,
    ZQA_MAX_SINGLE_SUBJECT_CAP,
    ZQA_MIN_ACADEMIC_SUBJECTS,
    ZQA_PILLAR_WEIGHTS,
    ZQA_SEL_KEYS,
)
from .core import classify_zqa_band, compute_spd
from .zqa_policy import issue_label, publish_blocking_issues

QUARTER_ORDER = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def normalize_score_0_100(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return _clamp(float(value), 0.0, 100.0)


def normalize_rating_0_5(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return _clamp(float(value), 0.0, 5.0)


def resolve_history_score(subject_scores: dict[str, float]) -> tuple[Optional[float], str]:
    social = subject_scores.get("social")
    hindi = subject_scores.get("hindi")
    if social is not None:
        return normalize_score_0_100(social), "social"
    if hindi is not None:
        return normalize_score_0_100(hindi), "hindi"
    return None, "none"


def resolve_academic_subjects(
    subject_scores: dict[str, float],
) -> tuple[dict[str, Optional[float]], str]:
    history, history_source = resolve_history_score(subject_scores)
    subjects = {
        "english": normalize_score_0_100(subject_scores.get("english")),
        "maths": normalize_score_0_100(subject_scores.get("maths")),
        "science": normalize_score_0_100(subject_scores.get("science")),
        "history": history,
    }
    return subjects, history_source


def count_academic_subjects(subjects: dict[str, Optional[float]]) -> int:
    return sum(1 for k in ZQA_ACADEMIC_KEYS if subjects.get(k) is not None)


def compute_academic_composite(subjects: dict[str, Optional[float]]) -> float:
    """Renormalize declared academic weights over present subjects only."""
    present = [
        (key, subjects[key], ZQA_ACADEMIC_WEIGHTS[key])
        for key in ZQA_ACADEMIC_KEYS
        if subjects.get(key) is not None
    ]
    if not present:
        return 0.0
    total_weight = sum(weight for _, _, weight in present)
    return sum(score * weight for _, score, weight in present) / total_weight


def _blooms_complete(blooms: Optional[dict[str, float]]) -> bool:
    if not blooms:
        return False
    return all(blooms.get(k) is not None for k in ZQA_BLOOMS_LEVEL_WEIGHTS)


def _sel_complete(sel: Optional[dict[str, float]]) -> bool:
    if not sel:
        return False
    return all(sel.get(k) is not None for k in ZQA_SEL_KEYS)


def compute_academic_core(
    subjects: dict[str, Optional[float]], *, history_source: str = "none"
) -> tuple[float, dict[str, Any]]:
    composite = compute_academic_composite(subjects)
    present = count_academic_subjects(subjects)
    meta: dict[str, Any] = {
        "english": subjects.get("english"),
        "maths": subjects.get("maths"),
        "science": subjects.get("science"),
        "history": subjects.get("history"),
        "history_source": history_source,
        "subjects_present": present,
        "subject_weights": dict(ZQA_ACADEMIC_WEIGHTS),
        "academic_core": round(composite, 2),
    }
    if present == 1:
        capped = min(composite, ZQA_MAX_SINGLE_SUBJECT_CAP)
        meta["single_subject_cap_applied"] = ZQA_MAX_SINGLE_SUBJECT_CAP
        return round(capped, 2), meta
    return round(composite, 2), meta


def compute_blooms_index(blooms: Optional[dict[str, float]]) -> tuple[Optional[float], dict[str, Any]]:
    if not blooms:
        return None, {"index_0_100": None, "levels": {}}
    levels: dict[str, float] = {}
    weighted = 0.0
    total_w = 0.0
    for key, weight in ZQA_BLOOMS_LEVEL_WEIGHTS.items():
        rating = normalize_rating_0_5(blooms.get(key))
        if rating is None:
            continue
        levels[key] = rating
        weighted += rating * weight
        total_w += weight
    if total_w <= 0:
        return None, {"index_0_100": None, "levels": levels}
    index = round((weighted / total_w) * 20.0, 2)
    return index, {"index_0_100": index, "levels": levels, "weights": dict(ZQA_BLOOMS_LEVEL_WEIGHTS)}


def compute_sel_index(sel: Optional[dict[str, float]]) -> tuple[Optional[float], dict[str, Any]]:
    if not sel:
        return None, {"index_0_100": None, "dimensions": {}}
    dims: dict[str, float] = {}
    vals = []
    for key in ZQA_SEL_KEYS:
        rating = normalize_rating_0_5(sel.get(key))
        if rating is None:
            continue
        dims[key] = rating
        vals.append(rating)
    if not vals:
        return None, {"index_0_100": None, "dimensions": dims}
    index = round((sum(vals) / len(vals)) * 20.0, 2)
    return index, {"index_0_100": index, "dimensions": dims}


def compute_pillar_composite(
    *,
    academic_score: float,
    blooms_score: Optional[float],
    sel_score: Optional[float],
    attendance_pct: float,
    require_all_pillars: bool,
) -> tuple[float, float, dict[str, Any]]:
    pillar_scores: dict[str, float] = {"academic": academic_score}
    if blooms_score is not None:
        pillar_scores["blooms"] = blooms_score
    if sel_score is not None:
        pillar_scores["sel"] = sel_score

    weights = dict(ZQA_PILLAR_WEIGHTS)
    active_weight = sum(weights[k] for k in pillar_scores)
    if active_weight <= 0:
        return 0.0, 0.0, {"pillars": {}, "weights_used": {}, "warnings": ["no_pillar_data"]}

    if require_all_pillars and len(pillar_scores) < 3:
        return 0.0, 0.0, {
            "pillars": {},
            "weights_used": {},
            "warnings": ["holistic_pillars_incomplete_for_publish"],
        }

    weights_used = {k: weights[k] / active_weight for k in pillar_scores}
    raw = sum(pillar_scores[k] * weights_used[k] for k in pillar_scores)

    floor = ZQA_ATTENDANCE_FLOOR_PCT
    if attendance_pct < floor:
        factor = max(0.55, attendance_pct / floor)
        warnings = [f"attendance_below_{int(floor)}_pct_integrity_factor"]
    else:
        factor = 1.0
        warnings = []

    composite = round(_clamp(raw * factor, 0.0, 100.0), 2)
    confidence = round((len(pillar_scores) / 3.0) * (1.0 if attendance_pct >= floor else 0.7), 3)

    return (
        composite,
        confidence,
        {
            "pillars": {k: round(v, 2) for k, v in pillar_scores.items()},
            "weights_used": {k: round(v, 3) for k, v in weights_used.items()},
            "attendance_integrity_factor": round(factor, 3),
            "warnings": warnings,
        },
    )


def validate_zqa_inputs(
    *,
    subject_scores: dict[str, float],
    blooms: Optional[dict[str, float]],
    sel: Optional[dict[str, float]],
    attendance_pct: float,
    avg_score: Optional[float],
    rank_in_class: Optional[str],
    class_size: Optional[int],
    finalized: bool,
    narrative: Optional[str] = None,
) -> list[str]:
    issues: list[str] = []
    subjects, _ = resolve_academic_subjects(subject_scores)
    present = count_academic_subjects(subjects)

    if finalized:
        if not blooms:
            issues.append("finalized_report_requires_blooms")
        elif not _blooms_complete(blooms):
            issues.append("finalized_report_incomplete_blooms")
        if not sel:
            issues.append("finalized_report_requires_sel")
        elif not _sel_complete(sel):
            issues.append("finalized_report_incomplete_sel")
        if present < ZQA_MIN_ACADEMIC_SUBJECTS:
            issues.append("finalized_report_requires_academic_subjects")
        if not rank_in_class or not str(rank_in_class).strip():
            issues.append("finalized_report_requires_rank")
        if class_size is None or int(class_size) < 1:
            issues.append("finalized_report_requires_class_size")
        if not narrative or not str(narrative).strip():
            issues.append("finalized_report_requires_narrative")

    if present == 0:
        issues.append("no_academic_subjects")

    if avg_score is not None and present >= 2:
        derived_vals = [
            v for v in (subjects.get("english"), subjects.get("maths"), subjects.get("science"), subjects.get("history"))
            if v is not None
        ]
        if derived_vals:
            derived_avg = sum(derived_vals) / len(derived_vals)
            if abs(float(avg_score) - derived_avg) > 15:
                issues.append("avg_score_materially_differs_from_subjects")

    if attendance_pct < ZQA_ATTENDANCE_FLOOR_PCT:
        issues.append("attendance_below_integrity_floor")

    return issues


@dataclass
class ZqaComputationResult:
    quarter: str
    zqa_composite: float
    zqa_band: str
    spd: float
    baseline_zqa: Optional[float]
    baseline_quarter: Optional[str]
    zqa_baseline_delta: float
    confidence: float
    academic: dict[str, Any]
    blooms: dict[str, Any]
    sel: dict[str, Any]
    pillars: dict[str, Any]
    validation_issues: list[str] = field(default_factory=list)
    zenq_contribution: Optional[float] = None
    zqa_published: bool = False
    attendance_pct_used: Optional[float] = None
    attendance_source: str = "profile_annual"

    def to_breakdown_dict(self) -> dict[str, Any]:
        return {
            "quarter": self.quarter,
            "zqa_composite": self.zqa_composite if self.zqa_published else None,
            "zqa_band": self.zqa_band if self.zqa_published else None,
            "zqa_published": self.zqa_published,
            "preview_composite": self.zqa_composite if not self.zqa_published else None,
            "spd": self.spd if self.zqa_published else None,
            "baseline_zqa": self.baseline_zqa if self.zqa_published else None,
            "baseline_quarter": self.baseline_quarter if self.zqa_published else None,
            "zqa_baseline_delta": self.zqa_baseline_delta if self.zqa_published else None,
            "confidence": self.confidence,
            "formula_version": "zqa_v2_holistic",
            "attendance_pct_used": self.attendance_pct_used,
            "attendance_source": self.attendance_source,
            "subject_scores_used": {
                "english": self.academic.get("english"),
                "maths": self.academic.get("maths"),
                "science": self.academic.get("science"),
                "history": self.academic.get("history"),
                "history_source": self.academic.get("history_source"),
            },
            "weights": {
                "academic_subject": dict(ZQA_ACADEMIC_WEIGHTS),
                "pillars": dict(ZQA_PILLAR_WEIGHTS),
            },
            "academic_core": self.academic,
            "blooms": self.blooms,
            "sel": self.sel,
            "pillars": self.pillars,
            "validation_issues": self.validation_issues,
            "publish_blockers": publish_blocking_issues(self.validation_issues),
            "publish_blocker_labels": [
                issue_label(code) for code in publish_blocking_issues(self.validation_issues)
            ],
            "zenq_contribution": self.zenq_contribution if self.zqa_published else None,
            "estimated_zenq_uplift": self.zenq_contribution,
        }


def pick_baseline_quarter(
    quarter_scores: dict[str, dict[str, float]], current_quarter: str
) -> Optional[str]:
    current_ord = QUARTER_ORDER.get(current_quarter.upper(), 99)
    candidates = [
        q
        for q in quarter_scores
        if q.upper() != current_quarter.upper() and QUARTER_ORDER.get(q.upper(), 99) < current_ord
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda q: QUARTER_ORDER.get(q.upper(), 99))[0]


def compute_zqa_result(
    *,
    quarter: str,
    subject_scores: dict[str, float],
    blooms: Optional[dict[str, float]],
    sel: Optional[dict[str, float]],
    attendance_pct: float,
    avg_score: Optional[float],
    rank_in_class: Optional[str],
    class_size: Optional[int],
    finalized: bool,
    narrative: Optional[str] = None,
    prior_quarter_subjects: dict[str, dict[str, float]],
    prior_quarter_blooms: Optional[dict[str, dict[str, float]]] = None,
    prior_quarter_sel: Optional[dict[str, dict[str, float]]] = None,
    attendance_source: str = "profile_annual",
) -> ZqaComputationResult:
    validation = validate_zqa_inputs(
        subject_scores=subject_scores,
        blooms=blooms,
        sel=sel,
        attendance_pct=attendance_pct,
        avg_score=avg_score,
        rank_in_class=rank_in_class,
        class_size=class_size,
        finalized=finalized,
        narrative=narrative,
    )
    blockers = publish_blocking_issues(validation)
    can_publish = finalized and not blockers

    subjects, history_source = resolve_academic_subjects(subject_scores)
    academic_score, academic_meta = compute_academic_core(subjects, history_source=history_source)
    blooms_score, blooms_meta = compute_blooms_index(blooms)
    sel_score, sel_meta = compute_sel_index(sel)

    composite, confidence, pillar_meta = compute_pillar_composite(
        academic_score=academic_score,
        blooms_score=blooms_score,
        sel_score=sel_score,
        attendance_pct=attendance_pct,
        require_all_pillars=can_publish,
    )

    if count_academic_subjects(subjects) < ZQA_MIN_ACADEMIC_SUBJECTS:
        composite = min(composite, ZQA_MAX_SINGLE_SUBJECT_CAP)
        pillar_meta.setdefault("warnings", []).append("insufficient_academic_subjects_final_cap")

    baseline_quarter = None
    baseline_zqa: Optional[float] = None
    delta = 0.0
    spd = 1.0

    if can_publish:
        baseline_quarter = pick_baseline_quarter(prior_quarter_subjects, quarter)
        if baseline_quarter:
            baseline_subjects, b_hist_src = resolve_academic_subjects(
                prior_quarter_subjects[baseline_quarter]
            )
            b_blooms = (prior_quarter_blooms or {}).get(baseline_quarter)
            b_sel = (prior_quarter_sel or {}).get(baseline_quarter)
            b_academic, _ = compute_academic_core(baseline_subjects, history_source=b_hist_src)
            b_blooms_score, _ = compute_blooms_index(b_blooms)
            b_sel_score, _ = compute_sel_index(b_sel)
            baseline_zqa, _, _ = compute_pillar_composite(
                academic_score=b_academic,
                blooms_score=b_blooms_score,
                sel_score=b_sel_score,
                attendance_pct=attendance_pct,
                require_all_pillars=True,
            )
        spd = compute_spd(baseline=baseline_zqa, current=composite)
        delta = round(composite - baseline_zqa, 2) if baseline_zqa is not None else 0.0

    band = classify_zqa_band(composite) if can_publish else "Not published"

    return ZqaComputationResult(
        quarter=quarter.upper(),
        zqa_composite=composite,
        zqa_band=band,
        spd=round(spd, 4),
        baseline_zqa=round(baseline_zqa, 2) if baseline_zqa is not None else None,
        baseline_quarter=baseline_quarter,
        zqa_baseline_delta=delta,
        confidence=confidence,
        academic=academic_meta,
        blooms=blooms_meta,
        sel=sel_meta,
        pillars=pillar_meta,
        validation_issues=validation,
        zqa_published=can_publish,
        attendance_pct_used=attendance_pct,
        attendance_source=attendance_source,
    )
