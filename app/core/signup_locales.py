"""Signup contact + address validation for supported countries."""

from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import HTTPException

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_IN_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")
_GB_MOBILE_NATIONAL_RE = re.compile(r"^7\d{9}$")
_IN_PIN_RE = re.compile(r"^[1-9]\d{5}$")
_GB_POSTCODE_RE = re.compile(
    r"^(?:GIR 0AA|(?:[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}))$",
    re.IGNORECASE,
)
_US_ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")
_CA_POSTAL_RE = re.compile(r"^[A-Z]\d[A-Z] \d[A-Z]\d$", re.IGNORECASE)

COUNTRY_ALIASES: dict[str, str] = {
    "in": "IN",
    "india": "IN",
    "gb": "GB",
    "uk": "GB",
    "united kingdom": "GB",
    "great britain": "GB",
    "us": "US",
    "usa": "US",
    "united states": "US",
    "ae": "AE",
    "uae": "AE",
}


@dataclass(frozen=True)
class CountryMeta:
    label: str
    dial: str
    mobile_min: int = 6
    mobile_max: int = 15
    postcode_mode: str = "generic"
    postcode_max: int = 12
    state_required: bool = False
    postcode_label: str = "Postal code"
    state_label: str = "State / province / region"
    city_label: str = "City"


def _meta(
    label: str,
    dial: str,
    *,
    mobile_min: int = 6,
    mobile_max: int = 15,
    postcode_mode: str = "generic",
    postcode_max: int = 12,
    state_required: bool = False,
    postcode_label: str = "Postal code",
    state_label: str = "State / province / region",
    city_label: str = "City",
) -> CountryMeta:
    return CountryMeta(
        label=label,
        dial=dial,
        mobile_min=mobile_min,
        mobile_max=mobile_max,
        postcode_mode=postcode_mode,
        postcode_max=postcode_max,
        state_required=state_required,
        postcode_label=postcode_label,
        state_label=state_label,
        city_label=city_label,
    )


COUNTRY_META: dict[str, CountryMeta] = {
    "IN": _meta(
        "India",
        "91",
        mobile_min=10,
        mobile_max=10,
        postcode_mode="in_pin",
        postcode_max=6,
        state_required=True,
        postcode_label="PIN code",
        state_label="State",
    ),
    "GB": _meta(
        "United Kingdom",
        "44",
        mobile_min=10,
        mobile_max=10,
        postcode_mode="uk",
        postcode_max=8,
        postcode_label="Postcode",
        state_label="County / region",
        city_label="Town / city",
    ),
    "US": _meta(
        "United States",
        "1",
        mobile_min=10,
        mobile_max=10,
        postcode_mode="us_zip",
        postcode_max=10,
        state_required=True,
        postcode_label="ZIP code",
        state_label="State",
    ),
    "CA": _meta(
        "Canada",
        "1",
        mobile_min=10,
        mobile_max=10,
        postcode_mode="ca_postal",
        postcode_max=7,
        state_required=True,
        state_label="Province / territory",
    ),
    "AU": _meta(
        "Australia",
        "61",
        mobile_min=9,
        mobile_max=9,
        postcode_mode="digits",
        postcode_max=4,
        state_required=True,
        state_label="State / territory",
        postcode_label="Postcode",
    ),
    "AE": _meta(
        "United Arab Emirates",
        "971",
        mobile_min=8,
        mobile_max=9,
        postcode_mode="optional",
        state_label="Emirate",
    ),
    "SG": _meta(
        "Singapore",
        "65",
        mobile_min=8,
        mobile_max=8,
        postcode_mode="digits",
        postcode_max=6,
        state_label="Region",
    ),
    "HK": _meta("Hong Kong", "852", mobile_min=8, mobile_max=8, postcode_mode="optional"),
    "QA": _meta("Qatar", "974", mobile_min=8, mobile_max=8, postcode_mode="optional"),
    "KW": _meta("Kuwait", "965", mobile_min=8, mobile_max=8, postcode_mode="optional"),
    "BH": _meta("Bahrain", "973", mobile_min=8, mobile_max=8, postcode_mode="optional"),
}

_EXTRA_COUNTRY_ROWS: list[tuple[str, str, str]] = [
    ("AD", "Andorra", "376"),
    ("AF", "Afghanistan", "93"),
    ("AG", "Antigua and Barbuda", "1"),
    ("AL", "Albania", "355"),
    ("AM", "Armenia", "374"),
    ("AO", "Angola", "244"),
    ("AR", "Argentina", "54"),
    ("AT", "Austria", "43"),
    ("AZ", "Azerbaijan", "994"),
    ("BA", "Bosnia and Herzegovina", "387"),
    ("BB", "Barbados", "1"),
    ("BD", "Bangladesh", "880"),
    ("BE", "Belgium", "32"),
    ("BF", "Burkina Faso", "226"),
    ("BG", "Bulgaria", "359"),
    ("BI", "Burundi", "257"),
    ("BJ", "Benin", "229"),
    ("BN", "Brunei", "673"),
    ("BO", "Bolivia", "591"),
    ("BR", "Brazil", "55"),
    ("BS", "Bahamas", "1"),
    ("BT", "Bhutan", "975"),
    ("BW", "Botswana", "267"),
    ("BY", "Belarus", "375"),
    ("BZ", "Belize", "501"),
    ("CH", "Switzerland", "41"),
    ("CL", "Chile", "56"),
    ("CN", "China", "86"),
    ("CO", "Colombia", "57"),
    ("CR", "Costa Rica", "506"),
    ("CU", "Cuba", "53"),
    ("CV", "Cape Verde", "238"),
    ("CY", "Cyprus", "357"),
    ("CZ", "Czech Republic", "420"),
    ("DE", "Germany", "49"),
    ("DJ", "Djibouti", "253"),
    ("DK", "Denmark", "45"),
    ("DM", "Dominica", "1"),
    ("DO", "Dominican Republic", "1"),
    ("DZ", "Algeria", "213"),
    ("EC", "Ecuador", "593"),
    ("EE", "Estonia", "372"),
    ("EG", "Egypt", "20"),
    ("ER", "Eritrea", "291"),
    ("ES", "Spain", "34"),
    ("ET", "Ethiopia", "251"),
    ("FI", "Finland", "358"),
    ("FJ", "Fiji", "679"),
    ("FR", "France", "33"),
    ("GA", "Gabon", "241"),
    ("GD", "Grenada", "1"),
    ("GE", "Georgia", "995"),
    ("GH", "Ghana", "233"),
    ("GM", "Gambia", "220"),
    ("GN", "Guinea", "224"),
    ("GQ", "Equatorial Guinea", "240"),
    ("GT", "Guatemala", "502"),
    ("GW", "Guinea-Bissau", "245"),
    ("GY", "Guyana", "592"),
    ("HN", "Honduras", "504"),
    ("HR", "Croatia", "385"),
    ("HT", "Haiti", "509"),
    ("HU", "Hungary", "36"),
    ("ID", "Indonesia", "62"),
    ("IE", "Ireland", "353"),
    ("IL", "Israel", "972"),
    ("IQ", "Iraq", "964"),
    ("IR", "Iran", "98"),
    ("IS", "Iceland", "354"),
    ("IT", "Italy", "39"),
    ("JM", "Jamaica", "1"),
    ("JO", "Jordan", "962"),
    ("JP", "Japan", "81"),
    ("KE", "Kenya", "254"),
    ("KR", "South Korea", "82"),
    ("KZ", "Kazakhstan", "7"),
    ("LA", "Laos", "856"),
    ("LB", "Lebanon", "961"),
    ("LC", "Saint Lucia", "1"),
    ("LI", "Liechtenstein", "423"),
    ("LK", "Sri Lanka", "94"),
    ("LR", "Liberia", "231"),
    ("LS", "Lesotho", "266"),
    ("LT", "Lithuania", "370"),
    ("LU", "Luxembourg", "352"),
    ("LV", "Latvia", "371"),
    ("LY", "Libya", "218"),
    ("MA", "Morocco", "212"),
    ("MC", "Monaco", "377"),
    ("MD", "Moldova", "373"),
    ("ME", "Montenegro", "382"),
    ("MG", "Madagascar", "261"),
    ("MK", "North Macedonia", "389"),
    ("ML", "Mali", "223"),
    ("MM", "Myanmar", "95"),
    ("MN", "Mongolia", "976"),
    ("MO", "Macau", "853"),
    ("MR", "Mauritania", "222"),
    ("MT", "Malta", "356"),
    ("MU", "Mauritius", "230"),
    ("MV", "Maldives", "960"),
    ("MW", "Malawi", "265"),
    ("MX", "Mexico", "52"),
    ("MY", "Malaysia", "60"),
    ("MZ", "Mozambique", "258"),
    ("NA", "Namibia", "264"),
    ("NE", "Niger", "227"),
    ("NG", "Nigeria", "234"),
    ("NI", "Nicaragua", "505"),
    ("NL", "Netherlands", "31"),
    ("NO", "Norway", "47"),
    ("NP", "Nepal", "977"),
    ("OM", "Oman", "968"),
    ("PA", "Panama", "507"),
    ("PE", "Peru", "51"),
    ("PG", "Papua New Guinea", "675"),
    ("PH", "Philippines", "63"),
    ("PK", "Pakistan", "92"),
    ("PL", "Poland", "48"),
    ("PR", "Puerto Rico", "1"),
    ("PS", "Palestine", "970"),
    ("PT", "Portugal", "351"),
    ("PY", "Paraguay", "595"),
    ("RO", "Romania", "40"),
    ("RS", "Serbia", "381"),
    ("RU", "Russia", "7"),
    ("RW", "Rwanda", "250"),
    ("SA", "Saudi Arabia", "966"),
    ("SB", "Solomon Islands", "677"),
    ("SC", "Seychelles", "248"),
    ("SD", "Sudan", "249"),
    ("SE", "Sweden", "46"),
    ("SI", "Slovenia", "386"),
    ("SK", "Slovakia", "421"),
    ("SL", "Sierra Leone", "232"),
    ("SM", "San Marino", "378"),
    ("SN", "Senegal", "221"),
    ("SO", "Somalia", "252"),
    ("SR", "Suriname", "597"),
    ("SS", "South Sudan", "211"),
    ("ST", "São Tomé and Príncipe", "239"),
    ("SV", "El Salvador", "503"),
    ("SY", "Syria", "963"),
    ("SZ", "Eswatini", "268"),
    ("TD", "Chad", "235"),
    ("TG", "Togo", "228"),
    ("TH", "Thailand", "66"),
    ("TJ", "Tajikistan", "992"),
    ("TL", "Timor-Leste", "670"),
    ("TM", "Turkmenistan", "993"),
    ("TN", "Tunisia", "216"),
    ("TR", "Turkey", "90"),
    ("TT", "Trinidad and Tobago", "1"),
    ("TW", "Taiwan", "886"),
    ("TZ", "Tanzania", "255"),
    ("UA", "Ukraine", "380"),
    ("UG", "Uganda", "256"),
    ("UY", "Uruguay", "598"),
    ("UZ", "Uzbekistan", "998"),
    ("VC", "Saint Vincent and the Grenadines", "1"),
    ("VE", "Venezuela", "58"),
    ("VN", "Vietnam", "84"),
    ("VU", "Vanuatu", "678"),
    ("YE", "Yemen", "967"),
    ("ZA", "South Africa", "27"),
    ("ZM", "Zambia", "260"),
    ("ZW", "Zimbabwe", "263"),
]

for code, label, dial in _EXTRA_COUNTRY_ROWS:
    COUNTRY_META.setdefault(code, _meta(label, dial))

SUPPORTED_COUNTRY_CODES = frozenset(COUNTRY_META.keys())


def _strip_control(value: str) -> str:
    return _CONTROL_CHARS.sub("", value or "").strip()


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _get_meta(country_code: str) -> CountryMeta:
    return COUNTRY_META[country_code]


def normalize_country_code(country: str) -> str:
    """Return ISO country code; reject unsupported values."""
    raw = _strip_control(country).upper()
    if raw in SUPPORTED_COUNTRY_CODES:
        return raw
    alias = COUNTRY_ALIASES.get((country or "").strip().lower())
    if alias:
        return alias
    raise HTTPException(
        status_code=400,
        detail="Select a supported country.",
    )


def _national_mobile_digits(mobile: str, country_code: str) -> str:
    national = _digits_only(mobile)
    if country_code == "GB" and national.startswith("0") and len(national) == 11:
        national = national[1:]
    return national


def _is_valid_national_mobile(national: str, country_code: str) -> bool:
    if country_code == "IN":
        return bool(_IN_MOBILE_RE.fullmatch(national))
    if country_code == "GB":
        return bool(_GB_MOBILE_NATIONAL_RE.fullmatch(national))
    meta = _get_meta(country_code)
    return meta.mobile_min <= len(national) <= meta.mobile_max


def validate_and_normalize_mobile(mobile: str, country: str) -> str:
    """Validate national or E.164 input; store E.164."""
    country_code = normalize_country_code(country)
    meta = _get_meta(country_code)
    raw = _strip_control(mobile)
    if not raw:
        raise HTTPException(status_code=400, detail="Mobile number is required.")

    if raw.startswith("+"):
        digits = _digits_only(raw)
        if not digits.startswith(meta.dial):
            raise HTTPException(
                status_code=400,
                detail=f"Enter a valid mobile for {meta.label} ({meta.dial}).",
            )
        national = digits[len(meta.dial) :]
    else:
        national = _national_mobile_digits(raw, country_code)

    if not _is_valid_national_mobile(national, country_code):
        raise HTTPException(
            status_code=400,
            detail=f"Enter a valid mobile number for {meta.label}.",
        )
    return f"+{meta.dial}{national}"


def normalize_uk_postcode(value: str) -> str:
    compact = re.sub(r"\s+", "", _strip_control(value).upper())
    if len(compact) < 5:
        return compact
    return f"{compact[:-3]} {compact[-3:]}"


def normalize_ca_postcode(value: str) -> str:
    compact = re.sub(r"\s+", "", _strip_control(value).upper())
    if len(compact) < 6:
        return compact
    return f"{compact[:3]} {compact[3:6]}"


def validate_and_normalize_postcode(pincode: str, country: str) -> str:
    country_code = normalize_country_code(country)
    meta = _get_meta(country_code)
    cleaned = _strip_control(pincode)

    if meta.postcode_mode == "optional":
        return cleaned[: meta.postcode_max]

    if not cleaned:
        raise HTTPException(status_code=400, detail=f"{meta.postcode_label} is required.")

    if meta.postcode_mode == "in_pin":
        digits = _digits_only(pincode)
        if not _IN_PIN_RE.fullmatch(digits):
            raise HTTPException(status_code=400, detail="PIN code must be 6 digits.")
        return digits

    if meta.postcode_mode == "uk":
        normalized = normalize_uk_postcode(pincode)
        if not _GB_POSTCODE_RE.fullmatch(normalized):
            raise HTTPException(
                status_code=400,
                detail="Enter a valid UK postcode (e.g. SW1A 1AA).",
            )
        return normalized

    if meta.postcode_mode == "us_zip":
        digits = _digits_only(pincode)
        formatted = f"{digits[:5]}-{digits[5:]}" if len(digits) == 9 else digits
        if not _US_ZIP_RE.fullmatch(formatted):
            raise HTTPException(status_code=400, detail="Enter a valid ZIP code.")
        return formatted

    if meta.postcode_mode == "ca_postal":
        normalized = normalize_ca_postcode(pincode)
        if not _CA_POSTAL_RE.fullmatch(normalized):
            raise HTTPException(
                status_code=400,
                detail="Enter a valid postal code (e.g. M5V 3L9).",
            )
        return normalized.upper()

    if meta.postcode_mode == "digits":
        digits = _digits_only(pincode)
        if len(digits) < 3:
            raise HTTPException(
                status_code=400,
                detail=f"Enter a valid {meta.postcode_label.lower()}.",
            )
        return digits[: meta.postcode_max]

    return cleaned[: meta.postcode_max]


def validate_state_field(state: str, country: str) -> str:
    country_code = normalize_country_code(country)
    meta = _get_meta(country_code)
    cleaned = _strip_control(state)[:120]
    if meta.state_required and not cleaned:
        raise HTTPException(status_code=400, detail=f"{meta.state_label} is required.")
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
    meta = _get_meta(code)
    national = _national_mobile_digits(raw, code)
    if _is_valid_national_mobile(national, code):
        return f"+{meta.dial}{national}"
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
    code = resolve_country_code(country)
    return _get_meta(code).label


def format_postcode_display(pincode: str | None, country: str | None) -> str:
    if not pincode or not str(pincode).strip():
        return "—"
    code = resolve_country_code(country)
    meta = _get_meta(code)
    if meta.postcode_mode == "uk":
        return normalize_uk_postcode(pincode)
    if meta.postcode_mode == "ca_postal":
        return normalize_ca_postcode(pincode)
    digits = _digits_only(pincode)
    return digits or _strip_control(pincode)


def locale_field_labels(country: str | None) -> dict[str, str]:
    code = resolve_country_code(country)
    meta = _get_meta(code)
    return {
        "postcode_label": meta.postcode_label,
        "state_label": meta.state_label,
        "city_label": meta.city_label,
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
