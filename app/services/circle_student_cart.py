"""Student-fund cart: members submit, leaders approve and pay."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.models.circle_ops import CartSubmissionStatus, CircleStudentCartSubmission
from app.models.signup import SignupRequest
from app.services.circle_budget import resolve_user_circle, _can_set_budget
from app.services.vendor_checkout import execute_cart_checkout, order_creates_from_submission_items
from app.microservices.vendor.schemas import CartCheckoutRequest


async def submit_student_cart(
    db: AsyncSession,
    user: SignupRequest,
    *,
    circle_id: str,
    items: list[dict],
    delivery_address: str,
    phone_number: str,
) -> dict[str, Any]:
    circle, role = await resolve_user_circle(db, user.id, circle_id)
    if not _member_in_circle(role):
        raise HTTPException(status_code=403, detail="You are not a member of this circle.")

    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    from app.services.circle_student_enrollment_gate import assert_circle_has_enrolled_student

    await assert_circle_has_enrolled_student(db, circle.id)

    total = sum(int(it.get("total_amount") or 0) for it in items)
    row = CircleStudentCartSubmission(
        circle_id=circle.id,
        submitted_by=user.id,
        status=CartSubmissionStatus.pending_leader.value,
        items_json=items,
        delivery_address=delivery_address.strip(),
        phone_number=phone_number.strip(),
        circle_name=circle.name,
        total_amount=total,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    await _notify_leaders_pending_cart(db, circle.id, circle.name, user.full_name, total)

    return _submission_out(row, submitter_name=user.full_name)


async def list_pending_carts(
    db: AsyncSession,
    leader: SignupRequest,
    circle_id: Optional[str] = None,
) -> list[dict]:
    circle, role = await resolve_user_circle(db, leader.id, circle_id)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can view pending cart submissions.")

    res = await db.execute(
        select(CircleStudentCartSubmission, SignupRequest.full_name)
        .join(SignupRequest, SignupRequest.id == CircleStudentCartSubmission.submitted_by)
        .where(
            CircleStudentCartSubmission.circle_id == circle.id,
            CircleStudentCartSubmission.status == CartSubmissionStatus.pending_leader.value,
        )
        .order_by(CircleStudentCartSubmission.created_at.desc())
    )
    return [_submission_out(row, submitter_name=name) for row, name in res.all()]


async def decide_student_cart(
    db: AsyncSession,
    leader: SignupRequest,
    submission_id: str,
    *,
    decision: str,
    circle_id: Optional[str] = None,
) -> dict[str, Any]:
    circle, role = await resolve_user_circle(db, leader.id, circle_id)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can approve cart submissions.")

    res = await db.execute(
        select(CircleStudentCartSubmission).where(CircleStudentCartSubmission.id == submission_id)
    )
    sub = res.scalar_one_or_none()
    if not sub or sub.circle_id != circle.id:
        raise HTTPException(status_code=404, detail="Cart submission not found.")
    if sub.status != CartSubmissionStatus.pending_leader.value:
        raise HTTPException(status_code=409, detail="Submission was already decided.")

    if decision == "rejected":
        sub.status = CartSubmissionStatus.rejected.value
        sub.decided_by = leader.id
        sub.decided_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(sub)
        submitter_res = await db.execute(
            select(SignupRequest).where(SignupRequest.id == sub.submitted_by)
        )
        submitter = submitter_res.scalar_one_or_none()
        return _submission_out(sub, submitter_name=submitter.full_name if submitter else "")

    submitter_res = await db.execute(select(SignupRequest).where(SignupRequest.id == sub.submitted_by))
    submitter = submitter_res.scalar_one_or_none()
    if not submitter:
        raise HTTPException(status_code=404, detail="Submitter account not found.")

    from app.services.circle_student_enrollment_gate import assert_circle_has_enrolled_student

    await assert_circle_has_enrolled_student(db, circle.id)

    checkout_body = CartCheckoutRequest(
        items=order_creates_from_submission_items(sub.items_json),
        delivery_address=sub.delivery_address,
        phone_number=sub.phone_number,
        order_type="student",
        circle_name=sub.circle_name or circle.name,
    )
    await execute_cart_checkout(db, checkout_body, leader)

    sub.status = CartSubmissionStatus.approved.value
    sub.decided_by = leader.id
    sub.decided_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sub)

    return _submission_out(sub, submitter_name=submitter.full_name)


def _member_in_circle(role: Optional[str]) -> bool:
    return bool(role)


def _submission_out(sub: CircleStudentCartSubmission, *, submitter_name: str) -> dict[str, Any]:
    return {
        "id": sub.id,
        "circle_id": sub.circle_id,
        "submitted_by": sub.submitted_by,
        "submitter_name": submitter_name,
        "status": sub.status,
        "items": sub.items_json,
        "delivery_address": sub.delivery_address,
        "phone_number": sub.phone_number,
        "total_amount": sub.total_amount,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "decided_at": sub.decided_at.isoformat() if sub.decided_at else None,
    }


async def _notify_leaders_pending_cart(
    db: AsyncSession,
    circle_id: str,
    circle_name: str,
    member_name: str,
    total: int,
) -> None:
    try:
        from app.models.notification import Notification
        from app.chat.models import CircleMember
        from app.services.circle_budget import LEADER_ROLES

        res = await db.execute(
            select(CircleMember.user_id).where(
                CircleMember.circle_id == circle_id,
                CircleMember.role.in_(list(LEADER_ROLES) + ["sponsor_leader"]),
            )
        )
        for (uid,) in res.all():
            db.add(
                Notification(
                    recipient_id=uid,
                    recipient_type="user",
                    notification_type="cart_pending_leader",
                    title="Student fund cart awaiting approval",
                    message=f"{member_name} submitted a student-fund cart (₹{total:,}) for {circle_name}.",
                    related_entity_id=circle_id,
                    related_entity_type="circle_cart",
                )
            )
        await db.commit()
    except Exception:
        pass
