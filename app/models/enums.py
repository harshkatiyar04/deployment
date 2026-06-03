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


