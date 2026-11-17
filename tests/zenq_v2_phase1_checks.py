"""ZenQ v2 Phase 1 checks — chat map, launch dials, session/target/pledge, PCS math.

Run: python -m tests.zenq_v2_phase1_checks
"""

from __future__ import annotations

from app.algorithms.zenq_v2 import CONSERVATIVE_LAUNCH_PARAMS, LAUNCH_PARAMS, score_event
from app.algorithms.zenq_v2.fade import fade_factor
from app.services.zenq_v2.chat_map import map_chat_event
from app.services.zenq_v2.ledger import pcs_from_month_totals


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_chat_map() -> None:
    _assert(map_chat_event(ras_score=0.9, substantive=True, shield_action="allow") == "CHAT_SUBST", "high ras SUBST")
    _assert(map_chat_event(ras_score=0.5, substantive=True, shield_action="ok") == "CHAT_ENCOUR", "mid ENCOUR")
    _assert(map_chat_event(ras_score=0.2, substantive=True, shield_action="allow") == "CHAT_SHARE", "low SHARE")
    _assert(map_chat_event(ras_score=0.9, substantive=False, shield_action="allow") == "CHAT_REACT", "nons SUBST→REACT")
    _assert(map_chat_event(ras_score=0.9, substantive=True, shield_action="block") is None, "blocked skip")
    _assert(map_chat_event(ras_score=0.5, substantive=True, shield_action="blocked") is None, "blocked skip 2")


def test_launch_chat_scoring() -> None:
    _, encour = score_event({"code": "CHAT_ENCOUR"}, "B", params=LAUNCH_PARAMS)
    _, subst = score_event({"code": "CHAT_SUBST"}, "B", params=LAUNCH_PARAMS)
    _, share = score_event({"code": "CHAT_SHARE"}, "B", params=LAUNCH_PARAMS)
    _, react = score_event({"code": "CHAT_REACT"}, "B", params=LAUNCH_PARAMS)
    _assert(encour > 0, "ENCOUR scored")
    _assert(subst > 0 and share > 0 and react > 0, "all chat codes scored under design product")
    _, subst_c = score_event({"code": "CHAT_SUBST"}, "B", params=CONSERVATIVE_LAUNCH_PARAMS)
    _assert(subst_c == 0.0, "SUBST off under conservative")


def test_session_target_pledge() -> None:
    cls, ip = score_event({"code": "SESSION", "minutes": 30}, "B")
    _assert(cls == "presence" and ip == 10.0, f"SESSION 30m B => 10 got {ip}")
    cls, ip = score_event({"code": "TARGET", "outcome": "full"}, "B")
    _assert(cls == "learning" and ip == 10.0, f"TARGET full => 10 got {ip}")
    cls, ip = score_event({"code": "PLEDGE_PAID", "pledge": 2000}, "B")
    _assert(cls == "funding" and ip == 15.0, f"PLEDGE 2000 => 15 got {ip}")


def test_partner_mult() -> None:
    _, home = score_event({"code": "SESSION", "minutes": 30, "partner_flag": "HOME"}, "B")
    _, eng = score_event({"code": "SESSION", "minutes": 30, "partner_flag": "ENGAGED"}, "B")
    _assert(abs(home - 15.0) < 1e-9, f"HOME {home}")
    _assert(abs(eng - 5.0) < 1e-9, f"ENGAGED {eng}")


def test_pcs_fade_math() -> None:
    raw = pcs_from_month_totals([100.0, 50.0], months_silent=0)
    _assert(abs(raw - 150.0) < 1e-9, f"no fade {raw}")
    faded = pcs_from_month_totals([100.0], months_silent=4)
    _assert(faded < 100.0, f"fade after silent {faded}")
    _assert(abs(fade_factor(3) - 1.0) < 1e-9, "fade starts after threshold")


def test_chat_never_maps_to_session_or_target() -> None:
    for ras, sub, shield in [
        (0.9, True, "allow"),
        (0.5, True, "ok"),
        (0.1, False, "allow"),
        (0.0, True, "block"),
    ]:
        code = map_chat_event(ras_score=ras, substantive=sub, shield_action=shield)
        if code is not None:
            _assert(code.startswith("CHAT_"), f"must be CHAT_* got {code}")
            _assert(code not in ("SESSION", "TARGET", "PLEDGE_PAID"), "no invent")


def test_ledger_flag_default_off_in_params_path() -> None:
    # Product = design dials on; conservative blob keeps historical gates.
    _assert(LAUNCH_PARAMS["flags"]["score_chat_subst"] is True, "product subst on")
    _assert(LAUNCH_PARAMS["agent_apply"] is True, "product agent on")
    _assert(CONSERVATIVE_LAUNCH_PARAMS["flags"]["score_chat_subst"] is False, "conservative subst off")
    _assert(CONSERVATIVE_LAUNCH_PARAMS["agent_apply"] is False, "conservative agent off")


def run_all() -> None:
    test_chat_map()
    test_launch_chat_scoring()
    test_session_target_pledge()
    test_partner_mult()
    test_pcs_fade_math()
    test_chat_never_maps_to_session_or_target()
    test_ledger_flag_default_off_in_params_path()
    print("zenq_v2_phase1_checks: all checks passed")


if __name__ == "__main__":
    run_all()
