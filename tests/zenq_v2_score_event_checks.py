"""ZenQ v2 Phase 0 — score_event product (design) dials (python -m tests.zenq_v2_score_event_checks)."""

from __future__ import annotations

from app.algorithms.zenq_v2 import (
    CONSERVATIVE_LAUNCH_PARAMS,
    DESIGN_PARAMS,
    LAUNCH_PARAMS,
    score_event,
    streak_mult,
)
from app.algorithms.zenq_v2.growth import G, growth_ratio
from app.algorithms.zenq_v2.fade import fade_factor
from app.algorithms.zenq_v2.agent_rules import propose_weight_deltas


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_product_params_are_design() -> None:
    _assert(LAUNCH_PARAMS["g_slope"] == 0.6, "product g_slope 0.6")
    _assert(LAUNCH_PARAMS["agent_apply"] is True, "product agent.apply true")
    flags = LAUNCH_PARAMS["flags"]
    _assert(flags["score_chat_subst"] is True, "chat subst on")
    _assert(flags["score_chat_share"] is True, "chat share on")
    _assert(flags["score_kia_effective"] is True, "kia effective on")
    _assert(flags["sponsor_yield"] is True, "sponsor yield on")
    _assert(flags["csr_tool"] is True, "csr tool on")
    _assert(DESIGN_PARAMS is LAUNCH_PARAMS or DESIGN_PARAMS["g_slope"] == 0.6, "design alias")
    cons = CONSERVATIVE_LAUNCH_PARAMS
    _assert(cons["g_slope"] == 0.0, "conservative g_slope 0")
    _assert(cons["agent_apply"] is False, "conservative agent off")


def test_session_target_pledge() -> None:
    cls, ip = score_event({"code": "SESSION", "minutes": 30}, "B")
    _assert(cls == "presence" and ip == 10.0, f"SESSION B 30m => 10, got {ip}")
    cls, ip = score_event({"code": "TARGET", "outcome": "full"}, "B")
    _assert(cls == "learning" and ip == 10.0, f"TARGET full => 10, got {ip}")
    cls, ip = score_event({"code": "PLEDGE_PAID", "pledge": 2000}, "B")
    _assert(cls == "funding" and ip == 15.0, f"PLEDGE ref => 15, got {ip}")


def test_chat_product_vs_conservative() -> None:
    _, encour = score_event({"code": "CHAT_ENCOUR"}, "B", params=LAUNCH_PARAMS)
    _, subst = score_event({"code": "CHAT_SUBST"}, "B", params=LAUNCH_PARAMS)
    _, share = score_event({"code": "CHAT_SHARE"}, "B", params=LAUNCH_PARAMS)
    _assert(encour == 2.5, f"ENCOUR scored: {encour}")
    _assert(subst == 1.5, f"SUBST scored under product: {subst}")
    _assert(share == 2.0, f"SHARE scored under product: {share}")
    _, subst_c = score_event({"code": "CHAT_SUBST"}, "B", params=CONSERVATIVE_LAUNCH_PARAMS)
    _assert(subst_c == 0.0, f"SUBST off under conservative: {subst_c}")


def test_kia_effective_on() -> None:
    _, practice = score_event({"code": "KIA_PRACTICE"}, "B", params=LAUNCH_PARAMS)
    _, effective = score_event({"code": "KIA_EFFECTIVE"}, "B", params=LAUNCH_PARAMS)
    _assert(practice == 4.0, f"PRACTICE on: {practice}")
    _assert(effective == 6.0, f"EFFECTIVE on: {effective}")
    _, eff_c = score_event({"code": "KIA_EFFECTIVE"}, "B", params=CONSERVATIVE_LAUNCH_PARAMS)
    _assert(eff_c == 0.0, "EFFECTIVE off under conservative")


def test_partner_home_engaged() -> None:
    _, home = score_event({"code": "SESSION", "minutes": 30, "partner_flag": "HOME"}, "B")
    _, eng = score_event({"code": "SESSION", "minutes": 30, "partner_flag": "ENGAGED"}, "B")
    _assert(abs(home - 15.0) < 1e-9, f"HOME ×1.5 => 15, got {home}")
    _assert(abs(eng - 5.0) < 1e-9, f"ENGAGED ×0.5 => 5, got {eng}")


def test_streak_and_g() -> None:
    _assert(streak_mult(0) == 1.0, "streak 0")
    _assert(abs(streak_mult(10) - 1.5) < 1e-9, "streak max")
    gr = growth_ratio(50.0, 56.0, 4, "B")
    _assert(gr is not None and gr > 0, "growth ratio positive")
    g_prod = G(gr, params=LAUNCH_PARAMS)
    _assert(g_prod > 1.0, f"product G > 1 when gr>0: {g_prod}")
    _assert(G(gr, params=CONSERVATIVE_LAUNCH_PARAMS) == 1.0, "conservative G always 1.0")


def test_fade_and_agent_log() -> None:
    _assert(fade_factor(0) == 1.0, "no fade early")
    _assert(fade_factor(3) == 1.0, "fade starts after threshold")
    _assert(fade_factor(4) < 1.0, "fade after silent months")
    deltas, fired, text = propose_weight_deltas(
        {"chat_share": 0.25, "mean_growth_ratio": 0.1, "mean_growth_ratio_3m": 0.2}
    )
    _assert("R1" in fired, f"R1 should fire: {fired}")
    _assert(deltas["chat"] < 0, "R1 reduces chat")


def main() -> None:
    test_product_params_are_design()
    test_session_target_pledge()
    test_chat_product_vs_conservative()
    test_kia_effective_on()
    test_partner_home_engaged()
    test_streak_and_g()
    test_fade_and_agent_log()
    print("zenq_v2_score_event_checks: OK")


if __name__ == "__main__":
    main()
