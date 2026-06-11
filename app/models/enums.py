import enum


class Persona(str, enum.Enum):
    sponsor = "sponsor"
    sponsor_leader = "sponsor_leader"
    sponsor_member = "sponsor_member"
    vendor = "vendor"
    student = "student"
    corporate = "corporate"
    mentor = "mentor"
    school = "school"


class KycStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    info_required = "info_required"


class MemberKind(str, enum.Enum):
    standard = "standard"
    parent_guardian = "parent_guardian"


class LoginAccessTier(str, enum.Enum):
    """Indian DPDPA-aligned: under-15 guardian-mediated; 15–17 verifiable consent; 18+ independent."""

    guardian_only = "guardian_only"
    consent_required = "consent_required"
    independent = "independent"


