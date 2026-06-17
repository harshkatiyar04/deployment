from typing import Any, Optional

from pydantic import BaseModel, Field


class StudentPseudonymCheckOut(BaseModel):
    available: bool
    pseudonym: str
    min_length: int = 8
    max_length: int = 24
    reason: Optional[str] = None


class StudentPseudonymSetRequest(BaseModel):
    pseudonym: str = Field(..., min_length=8, max_length=24)


class StudentPseudonymSetOut(BaseModel):
    pseudonym: str
    pseudonym_needs_setup: bool = False
    message: str = "Pseudonym saved."


class StudentProfileOut(BaseModel):
    signup_id: str
    pseudonym: str
    pseudonym_needs_setup: bool = False
    pseudonym_min_length: int = 8
    pseudonym_max_length: int = 24
    avatar_key: Optional[str] = None
    grade: Optional[str] = None
    school_label: Optional[str] = None
    login_access_tier: Optional[str] = None
    has_parental_consent: bool = False
    kyc_status: str
    circle_id: Optional[str] = None
    circle_name_masked: Optional[str] = None
    school_linked: bool = False


class StudentOverviewOut(BaseModel):
    signup_id: str
    pseudonym: str
    avatar_key: Optional[str] = None
    grade: Optional[str] = None
    school_label: Optional[str] = None
    circle_name_masked: Optional[str] = None
    school_linked: bool = False
    kpis: dict[str, Any] = {}
    school_note: Optional[str] = None
    milestones: list[dict[str, str]] = []


class StudentDashboardBundleOut(BaseModel):
    profile: StudentProfileOut
    overview: StudentOverviewOut
    timeline: dict[str, Any] = {}
    progress: dict[str, Any] = {}


class StudentCircleJoinRequest(BaseModel):
    circle_id: str = Field(..., min_length=1)


class StudentKiaChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class StudentKiaChatResponse(BaseModel):
    reply: str
    user_message_id: str
    kia_message_id: str


class StudentKiaMessageOut(BaseModel):
    id: str
    role: str
    text: str
    created_at: str


class StudentMentoringPostRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
