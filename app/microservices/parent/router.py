"""Parent guardian portal — linked child view and academic uploads."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_auth import get_current_user
from app.db.session import get_db
from app.microservices.parent.schemas import ParentChildOut, ParentSubmissionOut
from app.models.signup import SignupRequest
from app.services.parent_portal import (
    build_parent_academic_profile,
    build_parent_onboarding_timeline,
    create_parent_submission,
    list_linked_children,
    list_parent_submissions,
    require_parent_guardian,
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
