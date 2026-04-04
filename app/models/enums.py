import enum


class Persona(str, enum.Enum):
    sponsor = "sponsor"
    vendor = "vendor"
    student = "student"


class KycStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


