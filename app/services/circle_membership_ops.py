"""Circle member cap, removal requests, and limit-increase requests (admin-approved)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.models.circle_ops import (
    DEFAULT_MEMBER_LIMIT,
    MAX_MEMBER_LIMIT,
    REQUEST_CIRCLE_RENAME,
    REQUEST_MEMBER_LIMIT,
    REQUEST_MEMBER_REMOVAL,
    REQUEST_TYPES_MEMBERSHIP,
    REQUEST_TYPES_OTHER,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    CircleAdminRequest,
)
from app.models.signup import SignupRequest
from app.services.circle_budget import LEADER_ROLES, _can_set_budget

LEADER_MEMBER_ROLES = frozenset({"lead", "sponsor_leader", "coordinator"})


def circle_member_limit(circle: SponsorCircle) -> int:
    return int(circle.member_limit or DEFAULT_MEMBER_LIMIT)


async def count_circle_members(db: AsyncSession, circle_id: str) -> int:
    """Seats used toward member cap (sponsored student excluded)."""
    from app.services.student_circle_privacy import count_circle_seats

    return await count_circle_seats(db, circle_id)


async def _pending_request_exists(
    db: AsyncSession,
    *,
    circle_id: str,
    request_type: str,
    target_user_id: Optional[str] = None,
) -> bool:
    q = select(CircleAdminRequest.id).where(
        CircleAdminRequest.circle_id == circle_id,
        CircleAdminRequest.request_type == request_type,
        CircleAdminRequest.status == STATUS_PENDING,
    )
    if target_user_id:
        q = q.where(CircleAdminRequest.target_user_id == target_user_id)
    res = await db.execute(q.limit(1))
    return res.scalar_one_or_none() is not None


async def request_member_removal(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    leader: SignupRequest,
    target_user_id: str,
    comment: str,
) -> CircleAdminRequest:
    reason = (comment or "").strip()
    if len(reason) < 10:
        raise ValueError("Please provide a reason of at least 10 characters for ZenK admin.")

    if target_user_id == leader.id:
        raise ValueError("You cannot request removal of yourself.")

    target_cm = await db.execute(
        select(CircleMember, SignupRequest)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(
            CircleMember.circle_id == circle.id,
            CircleMember.user_id == target_user_id,
        )
    )
    row = target_cm.first()
    if not row:
        raise ValueError("That person is not a member of your circle.")
    cm, target_user = row
    if (cm.role or "").lower() in LEADER_MEMBER_ROLES:
        raise ValueError("Circle leaders cannot be removed through this flow. Contact ZenK support.")

    if await _pending_request_exists(
        db, circle_id=circle.id, request_type=REQUEST_MEMBER_REMOVAL, target_user_id=target_user_id
    ):
        raise ValueError("A pending removal request already exists for this member.")

    member_count = await count_circle_members(db, circle.id)
    req = CircleAdminRequest(
        id=str(uuid.uuid4()),
        circle_id=circle.id,
        request_type=REQUEST_MEMBER_REMOVAL,
        status=STATUS_PENDING,
        requested_by_user_id=leader.id,
        requested_by_name=leader.full_name,
        target_user_id=target_user.id,
        target_user_name=target_user.full_name,
        current_member_count=member_count,
        current_member_limit=circle_member_limit(circle),
        leader_comment=reason,
    )
    db.add(req)
    await db.flush()
    return req


async def request_member_limit_increase(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    leader: SignupRequest,
    requested_limit: int,
    comment: str,
) -> CircleAdminRequest:
    reason = (comment or "").strip()
    if len(reason) < 10:
        raise ValueError("Please explain why you need more members (at least 10 characters).")

    current_limit = circle_member_limit(circle)
    if requested_limit <= current_limit:
        raise ValueError(
            f"Requested limit must be higher than the current cap ({current_limit})."
        )
    if requested_limit > MAX_MEMBER_LIMIT:
        raise ValueError(f"Maximum allowed member limit is {MAX_MEMBER_LIMIT}.")

    if await _pending_request_exists(
        db, circle_id=circle.id, request_type=REQUEST_MEMBER_LIMIT
    ):
        raise ValueError("A pending member-limit request already exists for this circle.")

    member_count = await count_circle_members(db, circle.id)
    req = CircleAdminRequest(
        id=str(uuid.uuid4()),
        circle_id=circle.id,
        request_type=REQUEST_MEMBER_LIMIT,
        status=STATUS_PENDING,
        requested_by_user_id=leader.id,
        requested_by_name=leader.full_name,
        current_member_count=member_count,
        current_member_limit=current_limit,
        requested_limit=requested_limit,
        leader_comment=reason,
    )
    db.add(req)
    await db.flush()
    return req


def request_to_dict(req: CircleAdminRequest, *, circle_name: Optional[str] = None) -> dict[str, Any]:
    return {
        "id": req.id,
        "circle_id": req.circle_id,
        "circle_name": circle_name,
        "request_type": req.request_type,
        "status": req.status,
        "requested_by_user_id": req.requested_by_user_id,
        "requested_by_name": req.requested_by_name,
        "target_user_id": req.target_user_id,
        "target_user_name": req.target_user_name,
        "current_member_count": req.current_member_count,
        "current_member_limit": req.current_member_limit,
        "requested_limit": req.requested_limit,
        "current_circle_name": req.current_circle_name,
        "requested_circle_name": req.requested_circle_name,
        "leader_comment": req.leader_comment,
        "admin_comment": req.admin_comment,
        "reviewed_by_admin": req.reviewed_by_admin,
        "reviewed_at": req.reviewed_at.isoformat() if req.reviewed_at else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
    }


async def list_circle_admin_requests(
    db: AsyncSession, circle_id: str, *, status: Optional[str] = None
) -> list[dict[str, Any]]:
    q = (
        select(CircleAdminRequest, SponsorCircle.name)
        .join(SponsorCircle, SponsorCircle.id == CircleAdminRequest.circle_id)
        .where(CircleAdminRequest.circle_id == circle_id)
        .order_by(CircleAdminRequest.created_at.desc())
    )
    if status:
        q = q.where(CircleAdminRequest.status == status)
    res = await db.execute(q)
    return [request_to_dict(r, circle_name=name) for r, name in res.all()]


async def list_pending_admin_queue(
    db: AsyncSession,
    *,
    request_types: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    q = (
        select(CircleAdminRequest, SponsorCircle.name)
        .join(SponsorCircle, SponsorCircle.id == CircleAdminRequest.circle_id)
        .where(CircleAdminRequest.status == STATUS_PENDING)
        .order_by(CircleAdminRequest.created_at.asc())
    )
    if request_types is not None:
        q = q.where(CircleAdminRequest.request_type.in_(sorted(request_types)))
    res = await db.execute(q)
    return [request_to_dict(r, circle_name=name) for r, name in res.all()]


async def list_pending_membership_ops_queue(db: AsyncSession) -> list[dict[str, Any]]:
    return await list_pending_admin_queue(db, request_types=REQUEST_TYPES_MEMBERSHIP)


async def list_pending_other_requests_queue(db: AsyncSession) -> list[dict[str, Any]]:
    return await list_pending_admin_queue(db, request_types=REQUEST_TYPES_OTHER)


async def admin_review_request(
    db: AsyncSession,
    *,
    request_id: str,
    decision: str,
    admin_comment: str,
    admin_label: str = "ZenK Admin",
) -> CircleAdminRequest:
    decision = (decision or "").strip().lower()
    if decision not in (STATUS_APPROVED, STATUS_REJECTED):
        raise ValueError("decision must be 'approved' or 'rejected'.")

    note = (admin_comment or "").strip()
    if len(note) < 5:
        raise ValueError("Admin comment is required (at least 5 characters).")

    res = await db.execute(
        select(CircleAdminRequest).where(CircleAdminRequest.id == request_id)
    )
    req = res.scalar_one_or_none()
    if not req:
        raise ValueError("Request not found.")
    if req.status != STATUS_PENDING:
        raise ValueError(f"Request is already {req.status}.")

    circle_res = await db.execute(
        select(SponsorCircle).where(SponsorCircle.id == req.circle_id)
    )
    circle = circle_res.scalar_one_or_none()
    if not circle:
        raise ValueError("Circle not found.")

    if decision == STATUS_APPROVED:
        if req.request_type == REQUEST_MEMBER_REMOVAL:
            if not req.target_user_id:
                raise ValueError("Missing target member on removal request.")
            cm_res = await db.execute(
                select(CircleMember).where(
                    CircleMember.circle_id == circle.id,
                    CircleMember.user_id == req.target_user_id,
                )
            )
            cm = cm_res.scalar_one_or_none()
            if cm and (cm.role or "").lower() not in LEADER_MEMBER_ROLES:
                await db.delete(cm)
        elif req.request_type == REQUEST_MEMBER_LIMIT:
            if not req.requested_limit:
                raise ValueError("Missing requested limit.")
            circle.member_limit = int(req.requested_limit)
        elif req.request_type == REQUEST_CIRCLE_RENAME:
            from app.services.circle_rename_ops import apply_approved_circle_rename

            leader_res = await db.execute(
                select(SignupRequest).where(SignupRequest.id == req.requested_by_user_id)
            )
            leader = leader_res.scalar_one_or_none()
            await apply_approved_circle_rename(
                db,
                circle=circle,
                req=req,
                leader_name=(leader.full_name if leader else req.requested_by_name) or "Circle leader",
            )
    else:
        pass

    req.status = decision
    req.admin_comment = note
    req.reviewed_by_admin = admin_label
    req.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    return req


async def assert_can_add_member(db: AsyncSession, circle: SponsorCircle) -> None:
    """Raise ValueError if circle is at member cap."""
    count = await count_circle_members(db, circle.id)
    limit = circle_member_limit(circle)
    if count >= limit:
        raise ValueError(
            f"This circle has reached its member limit ({count}/{limit}). "
            "Request a limit increase from My Circle (admin approval required)."
        )


def member_row_flags(
    *,
    cm_role: str,
    user_id: str,
    leader_user_id: str,
    is_leader_viewer: bool,
) -> dict[str, bool]:
    from app.services.student_circle_privacy import is_beneficiary_role

    is_leader_role = (cm_role or "").lower() in LEADER_MEMBER_ROLES
    return {
        "is_removable": is_leader_viewer
        and not is_leader_role
        and not is_beneficiary_role(cm_role)
        and user_id != leader_user_id,
    }
