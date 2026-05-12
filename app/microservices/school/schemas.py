from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel


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
    welcome_sent: bool
    welcome_message: str
    task_list: List[dict]


class TutorRecommendationAction(BaseModel):
    action: str
