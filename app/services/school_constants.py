"""Shared school onboarding constants."""

SCHOOL_AFFILIATIONS = [
    {"id": "CBSE", "label": "CBSE"},
    {"id": "ICSE", "label": "ICSE / ISC"},
    {"id": "STATE", "label": "State Board"},
    {"id": "IB", "label": "IB / International"},
    {"id": "CIE", "label": "Cambridge (CIE)"},
    {"id": "OTHER", "label": "Other"},
]

VALID_AFFILIATION_IDS = {a["id"] for a in SCHOOL_AFFILIATIONS}
