from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator


class SchoolProfileResponse(BaseModel):
    id: str
    school_name: str
    school_code: str
    affiliation: str
    city: str
    district: str
    principal_name: str
    partner_since: Optional[str]
    is_partner: bool
    fy_current: str
    total_enrolled: int
    avg_attendance: float
    avg_academic_score: float
    next_zqa_date: Optional[str]
    reports_pending: int
    school_logo_url: Optional[str] = None
    principal_photo_url: Optional[str] = None


class SchoolPhotoUploadResponse(BaseModel):
    url: str
    message: str = "Photo updated"


class SchoolStudentResponse(BaseModel):
    id: str
    full_name: str
    grade: str
    circle_id: Optional[str]
    circle_name: Optional[str]
    attendance_pct: float
    avg_score: float
    zqa_score: float
    risk_level: str
    q_report_status: str
    tutor_recommendation: Optional[str]
    tutor_recommendation_status: str
    zenk_id: Optional[str] = None
    dob: Optional[str] = None
    class_teacher: Optional[str] = None
    sl_name: Optional[str] = None
    mentor_name: Optional[str] = None
    rank_in_class: Optional[str] = None
    class_size: Optional[int] = None
    zenq_contribution: Optional[float] = None
    zqa_baseline_delta: Optional[float] = None


class SchoolStudentSubjectScoreResponse(BaseModel):
    subject: str
    quarter: str
    score: float


class SchoolStudentBloomsAssessmentResponse(BaseModel):
    quarter: str
    remember: float
    understand: float
    apply: float
    analyse: float
    evaluate: float
    create: float
    assessed_by: Optional[str]


class SchoolStudentSELResponse(BaseModel):
    quarter: str
    self_awareness: float
    self_management: float
    social_awareness: float
    relationship_skills: float
    responsible_decisions: float


class SchoolStudentNarrativeResponse(BaseModel):
    quarter: str
    teacher_name: str
    narrative: str
    finalized: bool


class SchoolStudentDetailResponse(SchoolStudentResponse):
    subject_scores: List[SchoolStudentSubjectScoreResponse] = []
    blooms_assessments: List[SchoolStudentBloomsAssessmentResponse] = []
    sel_assessments: List[SchoolStudentSELResponse] = []
    narratives: List[SchoolStudentNarrativeResponse] = []


class SchoolReportResponse(BaseModel):
    id: str
    student_id: str
    student_name: str
    quarter: str
    fy: str
    submitted_at: Optional[str]
    kia_draft: Optional[str]
    status: str


class SchoolAttendanceResponse(BaseModel):
    student_id: str
    student_name: str
    month: int
    year: int
    attendance_pct: float
    working_days: int
    days_present: int


class SchoolAttendanceImportResponse(BaseModel):
    status: str
    message: str
    success_count: int
    errors: List[str] = []
    imported_by: str


class SchoolAttendanceEntryRequest(BaseModel):
    student_id: str
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2020, le=2035)
    working_days: int = Field(ge=1, le=31)
    days_present: int = Field(ge=0, le=31)

    @model_validator(mode="after")
    def present_not_above_working(self) -> "SchoolAttendanceEntryRequest":
        if self.days_present > self.working_days:
            raise ValueError("days_present cannot exceed working_days")
        return self


class SchoolAttendanceEntryResponse(BaseModel):
    status: str
    message: str
    record: SchoolAttendanceResponse


class SchoolZQAStudentResponse(BaseModel):
    student_id: str
    student_name: str
    grade: str
    circle_name: Optional[str]
    zqa_score: float
    risk_level: str
    trend: List[float]


class SchoolKiaPriorityItem(BaseModel):
    type: str
    title: str
    detail: str
    student_name: Optional[str] = None
    action_required: bool = False


class SchoolKiaPrioritiesResponse(BaseModel):
    greeting: str
    items: List[SchoolKiaPriorityItem]


class SchoolKiaChatRequest(BaseModel):
    message: str


class SchoolKiaChatResponse(BaseModel):
    reply: str


class SchoolKiaMessageResponse(BaseModel):
    id: str
    school_id: str
    role: str
    text: str
    created_at: str


class SchoolKiaWelcomeResponse(BaseModel):
    id: str
    welcome_sent: bool
    welcome_message: str
    task_list: List[str] = []


class TutorRecommendationAction(BaseModel):
    action: str


class SubjectScoresInput(BaseModel):
    maths: float = Field(ge=0, le=100)
    science: float = Field(ge=0, le=100)
    english: float = Field(ge=0, le=100)
    social: float = Field(ge=0, le=100)
    hindi: float = Field(ge=0, le=100)
    sanskrit: Optional[float] = Field(default=None, ge=0, le=100)


class BloomsInput(BaseModel):
    remember: float = Field(ge=0, le=5)
    understand: float = Field(ge=0, le=5)
    apply: float = Field(ge=0, le=5)
    analyse: float = Field(ge=0, le=5)
    evaluate: float = Field(ge=0, le=5)
    create: float = Field(ge=0, le=5)


class SELInput(BaseModel):
    self_awareness: float = Field(ge=0, le=5)
    self_management: float = Field(ge=0, le=5)
    social_awareness: float = Field(ge=0, le=5)
    relationship_skills: float = Field(ge=0, le=5)
    responsible_decisions: float = Field(ge=0, le=5)


class QuarterlyReportSubmitRequest(BaseModel):
    student_id: str
    quarter: str
    fy: str = "2025-26"
    attendance_pct: float = Field(ge=0, le=100)
    avg_score: float = Field(ge=0, le=100)
    risk_level: str
    rank_in_class: Optional[str] = None
    class_size: Optional[int] = None
    circle_name: Optional[str] = None
    subject_scores: SubjectScoresInput
    blooms: BloomsInput
    sel: SELInput
    narrative: str
    tutor_recommendation: Optional[str] = None
    ready_for_zenk: bool = True


class QuarterlyReportSubmitResponse(BaseModel):
    status: str
    message: str
    submission_id: str
    student_id: str
    student_name: str
    quarter: str
    submitted_by_name: str
    submitted_by_email: str
    submitted_at: str


class SchoolFormSubmissionResponse(BaseModel):
    id: str
    student_id: str
    student_name: str
    quarter: str
    fy: str
    source: str
    submitted_by_name: str
    submitted_by_email: str
    submitted_at: str
    status: str


class SchoolCsvImportRowResult(BaseModel):
    row: str
    student_name: str
    quarter: str
    submission_id: str


class SchoolCsvImportResponse(BaseModel):
    status: str
    message: str
    success_count: int
    errors: List[str] = []
    imported: List[SchoolCsvImportRowResult] = []


class SchoolPdfExtractResponse(BaseModel):
    status: str
    message: str
    review_id: str
    student_id: str
    student_name: str
    quarter: str
    confidence: Optional[str] = None
    notes: Optional[str] = None
    draft: dict


class SchoolPendingReviewResponse(BaseModel):
    id: str
    student_id: str
    student_name: str
    quarter: str
    fy: str
    source: str
    submitted_by_name: str
    submitted_at: str
    filename: Optional[str] = None
    confidence: Optional[str] = None
    notes: Optional[str] = None
    draft: dict


class SchoolCircleOption(BaseModel):
    id: str
    name: str
    description: str = ""


class InitialAcademicPayload(BaseModel):
    include_initial_report: bool = False
    quarter: str = "Q4"
    fy: str = "2025-26"
    attendance_pct: float = Field(default=0, ge=0, le=100)
    avg_score: float = Field(default=0, ge=0, le=100)
    risk_level: str = "Low"
    rank_in_class: Optional[str] = None
    class_size: Optional[int] = None
    subject_scores: Optional[SubjectScoresInput] = None
    blooms: Optional[BloomsInput] = None
    sel: Optional[SELInput] = None
    narrative: str = ""
    tutor_recommendation: Optional[str] = None
    ready_for_zenk: bool = False


class SchoolStudentEnrollRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    grade: str = Field(min_length=1, max_length=50)
    circle_id: str
    dob: Optional[str] = None
    zenk_id: Optional[str] = None
    class_teacher: Optional[str] = None
    sl_name: Optional[str] = None
    mentor_name: Optional[str] = None
    rank_in_class: Optional[str] = None
    class_size: Optional[int] = Field(default=None, ge=1, le=500)
    initial_academic_payload: Optional[InitialAcademicPayload] = None


class SchoolEnrollmentRequestResponse(BaseModel):
    id: str
    school_id: str
    school_name: Optional[str] = None
    circle_id: str
    circle_name: str
    status: str
    student_id: Optional[str] = None
    full_name: str
    grade: str
    dob: Optional[str] = None
    zenk_id: Optional[str] = None
    class_teacher: Optional[str] = None
    sl_name: Optional[str] = None
    mentor_name: Optional[str] = None
    rank_in_class: Optional[str] = None
    class_size: Optional[int] = None
    initial_academic_payload: Optional[dict] = None
    requested_by_name: str
    requested_by_email: str
    requested_at: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_note: Optional[str] = None
    intimation_sent_at: Optional[str] = None


class SchoolEnrollmentCreateResponse(BaseModel):
    status: str
    message: str
    request: SchoolEnrollmentRequestResponse


class CircleEnrollmentReviewRequest(BaseModel):
    review_note: Optional[str] = None


class CircleEnrollmentRejectRequest(BaseModel):
    review_note: str = Field(min_length=3, max_length=500)


class SchoolReviewApproveRequest(BaseModel):
    student_id: str
    quarter: str
    fy: str = "2025-26"
    attendance_pct: float = Field(ge=0, le=100)
    avg_score: float = Field(ge=0, le=100)
    risk_level: str
    rank_in_class: Optional[str] = None
    class_size: Optional[int] = None
    circle_name: Optional[str] = None
    subject_scores: SubjectScoresInput
    blooms: BloomsInput
    sel: SELInput
    narrative: str
    tutor_recommendation: Optional[str] = None
    ready_for_zenk: bool = True
