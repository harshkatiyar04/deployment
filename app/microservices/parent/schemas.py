from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ParentChildKpis(BaseModel):
    zqa_score: int = 0
    attendance_pct: int = 0
    avg_score: int = 0
    risk_level: str = "—"


class ParentChildCircleJoin(BaseModel):
    in_circle: bool = False
    pending_request: Optional[dict] = None
    can_request_join: bool = False
    block_reason: Optional[str] = None


class ParentChildOut(BaseModel):
    student_signup_id: str
    pseudonym: str
    grade: Optional[str] = None
    school_linked: bool = False
    school_student_id: Optional[str] = None
    circle_id: Optional[str] = None
    circle_name_masked: Optional[str] = None
    relationship: str = "parent"
    kpis: ParentChildKpis = Field(default_factory=ParentChildKpis)
    upload_eligible: bool = False
    upload_block_reason: Optional[str] = None
    circle_join: ParentChildCircleJoin = Field(default_factory=ParentChildCircleJoin)


class ParentGradeSubject(BaseModel):
    name: str
    grade: str


class ParentGradePayload(BaseModel):
    quarter: Optional[str] = None
    subjects: List[ParentGradeSubject] = Field(default_factory=list)


class ParentSubmissionOut(BaseModel):
    id: str
    student_signup_id: str
    school_student_id: Optional[str] = None
    document_type: str
    submission_kind: str = "file"
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    parent_note: Optional[str] = None
    grade_payload: Optional[ParentGradePayload] = None
    status: str
    principal_note: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: Optional[str] = None


class SchoolParentSubmissionOut(ParentSubmissionOut):
    student_name: Optional[str] = None
    grade: Optional[str] = None
    parent_signup_id: Optional[str] = None


class ParentReviewRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=2000)


class ParentRejectRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)
