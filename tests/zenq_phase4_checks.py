"""Phase 4 checks — spark, decay, welfare (run: python -m tests.zenq_phase4_checks)."""

from app.algorithms.zenq.core import compute_s, compute_ziq
from app.algorithms.zenq.decay import apply_zeq_decay, months_since
from app.algorithms.zenq.welfare import evaluate_welfare_level, welfare_level_label


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_spark_boosts_s_factor() -> None:
    base = compute_s(14, new_user=False, spark_active=False)
    sparked = compute_s(14, new_user=False, spark_active=True)
    _assert(sparked > base, "spark should boost S component")
    _assert(sparked <= 1.0, "S should stay capped at 1.0")


def test_decay_grace_then_fade() -> None:
    raw = 0.80
    unchanged, f0 = apply_zeq_decay(raw, 2)
    faded, f1 = apply_zeq_decay(raw, 5)
    _assert(unchanged == raw, "no decay within 2-month grace")
    _assert(f0 == 1.0, "decay factor 1.0 in grace")
    _assert(faded < raw, "decay after grace period")
    _assert(f1 < 1.0, "decay factor below 1 after grace")


def test_welfare_escalation() -> None:
    level, issues = evaluate_welfare_level({"sos_open": True})
    _assert(level == 3, "open SOS should be urgent")
    _assert("sos_report_open" in issues, "SOS issue tagged")

    level2, _ = evaluate_welfare_level({"max_sponsor_silence_days": 30, "critical_need": True})
    _assert(level2 == 3, "long silence + critical need is urgent")

    level1, issues1 = evaluate_welfare_level({"max_sponsor_silence_days": 15})
    _assert(level1 == 1, "14d+ silence is watch")
    _assert(welfare_level_label(level1) == "watch", "label matches")


def test_months_since_none_is_high() -> None:
    _assert(months_since(None) >= 99, "missing activity treated as very stale")


def test_decay_affects_ziq_chain() -> None:
    zeq = 0.75
    zcq = 1.0
    spd = 1.1
    ziq_raw = compute_ziq(zeq=zeq, zcq=zcq, spd=spd)
    zeq_decayed, _ = apply_zeq_decay(zeq, 6)
    ziq_decayed = compute_ziq(zeq=zeq_decayed, zcq=zcq, spd=spd)
    _assert(ziq_decayed < ziq_raw, "decayed ZEQ lowers ZIQ")


def run_all() -> None:
    test_spark_boosts_s_factor()
    test_decay_grace_then_fade()
    test_welfare_escalation()
    test_months_since_none_is_high()
    test_decay_affects_ziq_chain()
    print("zenq_phase4_checks: all checks passed")


if __name__ == "__main__":
    run_all()
