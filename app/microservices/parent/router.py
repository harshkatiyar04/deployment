"""Parent guardian portal — linked child view and academic uploads."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_auth import get_current_user
from app.db.session import get_db
from app.microservices.parent.schemas import ParentChildOut, ParentGradeExtractOut, ParentSubmissionOut
from app.services.parent_transcript_extract import extract_parent_grades_from_bytes
from app.models.signup import SignupRequest
from app.services.parent_portal import (
    ALLOWED_MIMES,
    MAX_FILE_BYTES,
    build_parent_academic_profile,
    build_parent_onboarding_timeline,
    create_parent_submission,
    list_linked_children,
    list_parent_submissions,
    require_parent_guardian,
    resolve_upload_mime,
)

router = APIRouter(prefix="/parent", tags=["parent-portal"])


@router.get("/onboarding/timeline")
async def parent_onboarding_timeline(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_parent_guardian(db, user)
    return await build_parent_onboarding_timeline(db, user)


@router.get("/academic-profile")
async def parent_academic_profile(
    quarter: str = "Q4",
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_parent_guardian(db, user)
    return await build_parent_academic_profile(db, user, quarter=quarter)


@router.get("/my-children", response_model=List[ParentChildOut])
async def my_children(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_parent_guardian(db, user)
    rows = await list_linked_children(db, user)
    return [ParentChildOut(**r) for r in rows]


@router.get("/academic-submissions", response_model=List[ParentSubmissionOut])
async def academic_submissions(
    student_signup_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_parent_guardian(db, user)
    rows = await list_parent_submissions(db, user, student_signup_id=student_signup_id)
    return [ParentSubmissionOut(**r) for r in rows]


@router.post("/academic-submissions/extract-grades", response_model=ParentGradeExtractOut)
async def extract_academic_grades(
    file: UploadFile = File(...),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_parent_guardian(db, user)
    content_type = resolve_upload_mime(file.content_type or "", file.filename or "")
    if content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail="Use PDF, JPG, PNG, or WebP")
    raw = await file.read()
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="File must be under 10 MB")
    try:
        result = await extract_parent_grades_from_bytes(
            raw,
            content_type=content_type,
            filename=file.filename or "",
        )
        return ParentGradeExtractOut(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/academic-submissions", response_model=ParentSubmissionOut)
async def upload_academic_submission(
    student_signup_id: str = Form(...),
    document_type: str = Form("marksheet"),
    file: Optional[UploadFile] = File(None),
    parent_note: Optional[str] = Form(None),
    quarter: Optional[str] = Form(None),
    maths_grade: Optional[str] = Form(None),
    science_grade: Optional[str] = Form(None),
    english_grade: Optional[str] = Form(None),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_parent_guardian(db, user)
    row = await create_parent_submission(
        db,
        user,
        student_signup_id=student_signup_id,
        document_type=document_type,
        file=file,
        parent_note=parent_note,
        quarter=quarter,
        maths_grade=maths_grade,
        science_grade=science_grade,
        english_grade=english_grade,
    )
    return ParentSubmissionOut(**row)
