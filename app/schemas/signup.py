from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import KycStatus, Persona


class KycDocumentOut(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    created_at: Optional[str] = None


class KycDocumentView(BaseModel):
    """KYC document with preview URL for UI viewing."""
    id: str
    original_filename: str
    preview_url: str  # URL to preview the document in browser (inline, not download)
    content_type: Optional[str] = None
    created_at: Optional[str] = None


class SignupResponse(BaseModel):
    id: str
    persona: Persona
    full_name: str
    mobile: str
    email: EmailStr
    kyc_status: KycStatus
    documents: list[KycDocumentOut] = []


class LinkedSignupSummary(BaseModel):
    """Linked student or parent/guardian on a family signup."""

    id: str
    full_name: str
    kyc_status: KycStatus
    member_kind: Optional[str] = None
    documents_count: int = 0


class AdminSignupListItem(BaseModel):
    """Admin queue item — email is plain str so dev/stored values like user@zenk still serialize."""

    id: str
    persona: Persona
    full_name: str
    mobile: str
    email: str
    kyc_status: KycStatus
    documents: list[KycDocumentOut] = []
    created_at: Optional[str] = None
    documents_count: int = 0
    member_kind: Optional[str] = None
    linked_student_signup_id: Optional[str] = None
    onboarding_version: Optional[str] = None
    display_role: Optional[str] = None


class AdminDecisionRequest(BaseModel):
    decision: KycStatus  # approved | rejected | info_required
    note: Optional[str] = None


class FullSignupDetails(BaseModel):
    """Complete signup details for admin review (excluding password)."""
    id: str
    persona: Persona
    kyc_status: KycStatus
    admin_note: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    # Common fields
    full_name: str
    mobile: str
    email: str
    address_line1: str
    address_line2: str
    city: str
    state: str
    pincode: str
    country: str

    # Sponsor fields
    sponsor_type: Optional[str] = None
    pan_number: Optional[str] = None
    company_name: Optional[str] = None
    company_registration_number: Optional[str] = None
    gst_number: Optional[str] = None
    authorized_signatory_name: Optional[str] = None
    authorized_signatory_designation: Optional[str] = None
    
    # School partner fields
    school_name: Optional[str] = None
    school_principal_name: Optional[str] = None
    school_affiliation: Optional[str] = None
    school_affiliation_number: Optional[str] = None
    school_enrollment_year: Optional[str] = None

    # Vendor fields
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    product_categories: Optional[str] = None
    website: Optional[str] = None
    
    # Student fields
    date_of_birth: Optional[str] = None  # ISO date string
    school_or_college_name: Optional[str] = None
    selected_school_id: Optional[str] = None
    grade_or_year: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_mobile: Optional[str] = None
    guardian_relationship: Optional[str] = None
    login_access_tier: Optional[str] = None
    member_kind: Optional[str] = None
    linked_student_signup_id: Optional[str] = None
    onboarding_version: Optional[str] = None
    linked_guardian: Optional[LinkedSignupSummary] = None
    linked_student: Optional[LinkedSignupSummary] = None
    
    # Documents metadata
    documents: list[KycDocumentOut] = []


# Base64-encoded file for JSON API
class KycDocumentBase64(BaseModel):
    filename: str = Field(..., description="Original filename (e.g., 'pan_card.pdf')")
    content_base64: str = Field(..., description="Base64-encoded file content")
    content_type: Optional[str] = Field(default=None, description="MIME type (e.g., 'application/pdf')")


# Common address fields
class AddressFields(BaseModel):
    full_name: str
    mobile: str
    email: EmailStr
    address_line1: str
    address_line2: str
    city: str
    state: str
    pincode: str
    country: str


# Sponsor signup request
class SponsorSignupRequest(AddressFields):
    sponsor_type: str = Field(..., description="Must be 'individual' or 'company'")
    pan_number: Optional[str] = None
    company_name: Optional[str] = None
    company_registration_number: Optional[str] = None
    gst_number: Optional[str] = None
    authorized_signatory_name: Optional[str] = None
    authorized_signatory_designation: Optional[str] = None
    kyc_docs: list[KycDocumentBase64] = Field(..., min_length=1, description="List of base64-encoded KYC documents")


# Vendor signup request
class VendorSignupRequest(AddressFields):
    business_name: str
    business_type: str
    gst_number: str
    pan_number: str
    product_categories: str
    website: str
    kyc_docs: list[KycDocumentBase64] = Field(..., min_length=1, description="List of base64-encoded KYC documents")


# Student signup request
class StudentSignupRequest(AddressFields):
    date_of_birth: date
    school_or_college_name: str
    grade_or_year: str
    guardian_name: str
    guardian_mobile: str
    guardian_relationship: str = Field(default="parent", description="parent, guardian, mother, father, etc.")
    circle_invite_code: Optional[str] = None
    parent_pan_number: Optional[str] = None
    kyc_docs: list[KycDocumentBase64] = Field(..., min_length=1, description="List of base64-encoded KYC documents")


class StudentFamilySignupResponse(SignupResponse):
    parent_signup_id: Optional[str] = None
    login_access_tier: Optional[str] = None
    family_link_id: Optional[str] = None
    school_referral_url: Optional[str] = None


