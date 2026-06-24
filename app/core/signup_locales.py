"""Signup contact + address validation for supported countries (IN, GB)."""

from __future__ import annotations

import re

from fastapi import HTTPException

SUPPORTED_COUNTRY_CODES = frozenset({"IN", "GB"})

COUNTRY_ALIASES: dict[str, str] = {
    "in": "IN",
    "india": "IN",
    "gb": "GB",
    "uk": "GB",
    "united kingdom": "GB",
    "great britain": "GB",
}

_IN_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")
_GB_MOBILE_NATIONAL_RE = re.compile(r"^7\d{9}$")
_IN_PIN_RE = re.compile(r"^[1-9]\d{5}$")
_GB_POSTCODE_RE = re.compile(
    r"^(?:GIR 0AA|(?:[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}))$",
    re.IGNORECASE,
)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _strip_control(value: str) -> str:
    return _CONTROL_CHARS.sub("", value or "").strip()


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_country_code(country: str) -> str:
    """Return ISO country code IN or GB; reject anything else."""
    raw = _strip_control(country).upper()
    if raw in SUPPORTED_COUNTRY_CODES:
        return raw
    alias = COUNTRY_ALIASES.get((country or "").strip().lower())
    if alias:
        return alias
    raise HTTPException(
        status_code=400,
        detail="Country must be India (IN) or United Kingdom (GB).",
    )


def validate_and_normalize_mobile(mobile: str, country: str) -> str:
    """Validate national or E.164 input; store E.164 (+91… / +44…)."""
    country_code = normalize_country_code(country)
    raw = _strip_control(mobile)
    if not raw:
        raise HTTPException(status_code=400, detail="Mobile number is required.")

    if raw.startswith("+"):
        digits = _digits_only(raw)
        if country_code == "IN":
            if not (digits.startswith("91") and len(digits) == 12):
                raise HTTPException(
                    status_code=400,
                    detail="Enter a valid Indian mobile (+91 followed by 10 digits).",
                )
            national = digits[2:]
        else:
            if not (digits.startswith("44") and len(digits) == 12):
                raise HTTPException(
                    status_code=400,
                    detail="Enter a valid UK mobile (+44 followed by 10 digits).",
                )
            national = digits[2:]
    else:
        national = _digits_only(raw)
        if country_code == "GB" and national.startswith("0") and len(national) == 11:
            national = national[1:]

    if country_code == "IN":
        if not _IN_MOBILE_RE.fullmatch(national):
            raise HTTPException(
                status_code=400,
                detail="Enter a valid 10-digit Indian mobile number.",
            )
        return f"+91{national}"

    if not _GB_MOBILE_NATIONAL_RE.fullmatch(national):
        raise HTTPException(
            status_code=400,
            detail="Enter a valid UK mobile number (e.g. 07xxx or 7xxx).",
        )
    return f"+44{national}"


def normalize_uk_postcode(value: str) -> str:
    compact = re.sub(r"\s+", "", _strip_control(value).upper())
    if len(compact) < 5:
        return compact
    return f"{compact[:-3]} {compact[-3:]}"


def validate_and_normalize_postcode(pincode: str, country: str) -> str:
    country_code = normalize_country_code(country)
    if country_code == "IN":
        digits = _digits_only(pincode)
        if not _IN_PIN_RE.fullmatch(digits):
            raise HTTPException(status_code=400, detail="PIN code must be 6 digits.")
        return digits

    normalized = normalize_uk_postcode(pincode)
    if not _GB_POSTCODE_RE.fullmatch(normalized):
        raise HTTPException(
            status_code=400,
            detail="Enter a valid UK postcode (e.g. SW1A 1AA).",
        )
    return normalized


def validate_state_field(state: str, country: str) -> str:
    country_code = normalize_country_code(country)
    cleaned = _strip_control(state)[:120]
    if country_code == "IN" and not cleaned:
        raise HTTPException(status_code=400, detail="State is required.")
    return cleaned


def sanitize_address_line(value: str, *, field: str = "Address", max_len: int = 200) -> str:
    cleaned = _strip_control(value)[:max_len]
    if not cleaned:
        raise HTTPException(status_code=400, detail=f"{field} is required.")
    return cleaned


def sanitize_optional_address_line(value: str, *, max_len: int = 200) -> str:
    return _strip_control(value)[:max_len]


def sanitize_city(value: str) -> str:
    cleaned = _strip_control(value)[:120]
    if not cleaned:
        raise HTTPException(status_code=400, detail="City is required.")
    return cleaned


def validate_signup_contact_address(
    *,
    mobile: str,
    country: str,
    pincode: str,
    state: str,
    city: str,
    address_line1: str,
    address_line2: str,
) -> tuple[str, str, str, str, str, str, str]:
    """Normalize and validate signup address bundle; returns stored values."""
    country_norm = normalize_country_code(country)
    mobile_norm = validate_and_normalize_mobile(mobile, country_norm)
    pincode_norm = validate_and_normalize_postcode(pincode, country_norm)
    state_norm = validate_state_field(state, country_norm)
    city_norm = sanitize_city(city)
    line1 = sanitize_address_line(address_line1, field="Address line 1")
    line2 = sanitize_optional_address_line(address_line2)
    return mobile_norm, country_norm, pincode_norm, state_norm, city_norm, line1, line2


COUNTRY_DISPLAY: dict[str, str] = {
    "IN": "India",
    "GB": "United Kingdom",
}


def resolve_country_code(country: str | None) -> str:
    """Best-effort country code for display; defaults to IN."""
    if not country:
        return "IN"
    try:
        return normalize_country_code(country)
    except HTTPException:
        return "IN"


def coerce_stored_mobile(mobile: str | None, country: str | None) -> str:
    """Normalize legacy national numbers to E.164 when country is known."""
    raw = _strip_control(mobile or "")
    if not raw:
        return ""
    if raw.startswith("+"):
        return raw

    code = resolve_country_code(country)
    digits = _digits_only(raw)
    if code == "IN" and len(digits) == 10 and _IN_MOBILE_RE.fullmatch(digits):
        return f"+91{digits}"
    if code == "GB":
        national = digits[1:] if digits.startswith("0") and len(digits) == 11 else digits
        if len(national) == 10 and _GB_MOBILE_NATIONAL_RE.fullmatch(national):
            return f"+44{national}"
    return raw


def format_mobile_display(mobile: str | None, country: str | None) -> str:
    """Human-readable phone for admin UI."""
    e164 = coerce_stored_mobile(mobile, country)
    if not e164:
        return "—"
    if e164.startswith("+91") and len(e164) == 13:
        national = e164[3:]
        return f"+91 {national[:5]} {national[5:]}"
    if e164.startswith("+44") and len(e164) == 13:
        national = e164[3:]
        return f"+44 {national[:4]} {national[4:]}"
    return e164


def format_country_display(country: str | None) -> str:
    return COUNTRY_DISPLAY.get(resolve_country_code(country), country or "—")


def format_postcode_display(pincode: str | None, country: str | None) -> str:
    if not pincode or not str(pincode).strip():
        return "—"
    code = resolve_country_code(country)
    if code == "GB":
        return normalize_uk_postcode(pincode)
    digits = _digits_only(pincode)
    return digits or _strip_control(pincode)


def locale_field_labels(country: str | None) -> dict[str, str]:
    code = resolve_country_code(country)
    if code == "GB":
        return {
            "postcode_label": "Postcode",
            "state_label": "County / region",
            "city_label": "Town / city",
        }
    return {
        "postcode_label": "PIN code",
        "state_label": "State",
        "city_label": "City",
    }


def build_contact_display(
    *,
    mobile: str | None,
    guardian_mobile: str | None = None,
    country: str | None,
    pincode: str | None = None,
) -> dict[str, str | None]:
    """Structured contact fields for admin APIs and exports."""
    labels = locale_field_labels(country)
    mobile_e164 = coerce_stored_mobile(mobile, country) or None
    guardian_e164 = coerce_stored_mobile(guardian_mobile, country) or None if guardian_mobile else None
    return {
        "country_code": resolve_country_code(country),
        "country_label": format_country_display(country),
        "mobile_display": format_mobile_display(mobile, country),
        "mobile_e164": mobile_e164,
        "guardian_mobile_display": format_mobile_display(guardian_mobile, country)
        if guardian_mobile
        else None,
        "guardian_mobile_e164": guardian_e164,
        "postcode_label": labels["postcode_label"],
        "postcode_display": format_postcode_display(pincode, country),
        "state_label": labels["state_label"],
        "city_label": labels["city_label"],
    }

