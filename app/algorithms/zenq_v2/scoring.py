"""Event scoring — Tech Guide §4 / board O.3 score_event."""

from __future__ import annotations

from typing import Any, Optional

from app.algorithms.zenq_v2.params import BRACKET, LAUNCH_PARAMS


def streak_mult(consecutive_active_weeks: int, params: Optional[dict[str, Any]] = None) -> float:
    p = params or LAUNCH_PARAMS
    step = float(p["streak_step"])
    mx = int(p["streak_max_wk"])
    return 1.0 + step * min(mx, max(0, consecutive_active_weeks))


def session_ip(minutes: float, bracket: str, params: Optional[dict[str, Any]] = None) -> float:
    p = params or LAUNCH_PARAMS
    b = BRACKET[bracket]
    norm = float(b["norm"])
    base = float(p["session_ip"]) * min(minutes / norm, 1.0)
    bonus = float(p["session_bonus"]) if minutes >= 1.5 * norm else 0.0
    return base + bonus


def partner_mult(flag: Optional[str], params: Optional[dict[str, Any]] = None) -> float:
    p = params or LAUNCH_PARAMS
    if flag == "HOME":
        return float(p["own_x"])
    if flag == "ENGAGED":
        return float(p["ext_x"])
    return 1.0


def credits_member_pcs(partner_flag: Optional[str]) -> bool:
    """T8: ENGAGED paid work never credits member PCS / home circle aggregates."""
    return partner_flag != "ENGAGED"


def _chat_scored(code: str, params: dict[str, Any]) -> bool:
    flags = params.get("flags") or {}
    if code == "CHAT_ENCOUR":
        return True
    if code == "CHAT_SUBST":
        return bool(flags.get("score_chat_subst", False))
    if code == "CHAT_SHARE":
        return bool(flags.get("score_chat_share", False))
    if code == "CHAT_REACT":
        return bool(flags.get("score_chat_react", False))
    return False


def score_event(
    event: dict[str, Any],
    bracket: str,
    streak_weeks: int = 0,
    params: Optional[dict[str, Any]] = None,
) -> tuple[str, float]:
    """Return (class, ip_final) for one ledger event.

    event keys: code, minutes?, outcome?, pledge?, partner_flag?
    Chat/Kia codes that are flagged off at launch return ip_final 0 but keep class
    so they can still be logged for later re-scoring under a new weights version.
    """
    p = params or LAUNCH_PARAMS
    code = str(event["code"])
    b = BRACKET.get(bracket) or BRACKET["B"]
    s = streak_mult(streak_weeks, p)

    if code == "SESSION":
        flag = event.get("partner_flag")
        mult = partner_mult(flag, p)
        base = session_ip(float(event.get("minutes") or 0), bracket, p) * float(b["w_pres"]) * s
        if flag == "ENGAGED":
            # Hiring-circle partner pool only (ext_x); never member PCS (T8)
            return "partner", float(base * mult)
        return "presence", float(base * mult)

    if code == "TARGET":
        flag = event.get("partner_flag")
        mult = partner_mult(flag, p)
        outcome = str(event.get("outcome") or "none")
        raw = float(p["target_ip"].get(outcome, 0)) * float(b["w_learn"]) * s
        if flag == "ENGAGED":
            return "partner", float(raw * mult)
        return "learning", float(raw * mult)

    if code.startswith("CHAT_"):
        kind = code[5:]  # SUBST / ENCOUR / SHARE / REACT
        raw = float(p["chat_ip"].get(kind, 0))
        ip = raw * float(b["w_chat"]) if _chat_scored(code, p) else 0.0
        return "chat", float(ip)

    if code.startswith("KIA_"):
        kind = code[4:]  # PRACTICE / PREP / EFFECTIVE
        raw = float(p["kia_ip"].get(kind, 0))
        if kind == "EFFECTIVE" and not (p.get("flags") or {}).get("score_kia_effective", False):
            return "kia", 0.0
        return "kia", float(raw * float(b["w_kia"]))

    if code == "PLEDGE_PAID":
        pledge = float(event.get("pledge") or 0)
        ref = float(p["fund_ref_inr"])
        cap_x = float(p["fund_cap_x"])
        return "funding", float(p["fund_ip"]) * min(pledge / ref, cap_x)

    if code == "REFERRAL_ACTIVATED":
        return "growth", float(p["referral_ip"])

    if code == "REFERRAL_ANNIVERSARY":
        return "growth", float(p["anniversary_ip"])

    if code == "SPARK":
        return "spark", float(p["spark_ip"])

    if code == "REVERSAL":
        # Caller supplies negative of original ip via event['ip_final']
        return str(event.get("class") or "presence"), float(event.get("ip_final") or 0)

    raise ValueError(f"unknown event code: {code}")
