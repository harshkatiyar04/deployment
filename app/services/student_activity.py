"""Student dashboard activity feed — notifications + onboarding/circle events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import KycStatus, LoginAccessTier
from app.models.notification import Notification
from app.models.signup import SignupRequest
from app.models.student_family import StudentFamilyLink
from app.models.student_onboarding import StudentCircleInterestRequest, StudentSchoolInterest
from app.services.student_onboarding_v2 import build_onboarding_timeline, resolve_school_student


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.isoformat()


def _item(
    *,
    item_id: str,
    source: str,
    category: str,
    severity: str,
    title: str,
    message: str,
    created_at: str,
    is_read: bool = False,
    action_tab: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "source": source,
        "category": category,
        "severity": severity,
        "title": title,
        "message": message,
        "created_at": created_at,
        "is_read": is_read,
        "action_tab": action_tab,
    }


_CATEGORY_BY_TYPE = {
    "kyc_approved": "kyc",
    "kyc_rejected": "kyc",
    "kyc_info_required": "kyc",
    "school_enrollment_approved": "school",
    "school_enrollment_rejected": "school",
    "school_admitted": "school",
    "circle_member_approved": "circle",
    "circle_member_rejected": "circle",
    "circle_interest_accepted": "circle",
    "circle_interest_rejected": "circle",
    "circle_probe_message": "circle",
    "parent_upload_approved": "parent",
    "parent_upload_rejected": "parent",
}


def _severity_for_type(notification_type: str) -> str:
    if notification_type in {"kyc_rejected", "school_enrollment_rejected", "circle_member_rejected", "circle_interest_rejected", "parent_upload_rejected"}:
        return "warning"
    if notification_type in {"kyc_approved", "school_enrollment_approved", "school_admitted", "circle_member_approved", "circle_interest_accepted", "parent_upload_approved"}:
        return "success"
    if notification_type in {"kyc_info_required"}:
        return "action"
    return "info"


def _action_tab_for_type(notification_type: str) -> Optional[str]:
    if notification_type.startswith("kyc"):
        return "Settings"
    if notification_type.startswith("school"):
        return "Overview"
    if notification_type.startswith("circle"):
        return "Join Circle"
    if notification_type.startswith("parent"):
        return "Overview"
    return "Overview"


async def build_student_activity_feed(
    db: AsyncSession,
    student: SignupRequest,
    *,
    limit: int = 40,
) -> dict[str, Any]:
    """Merged feed for the student notification panel."""
    items: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    notif_res = await db.execute(
        select(Notification)
        .where(
            Notification.recipient_id == student.id,
            Notification.recipient_type == "user",
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    for n in notif_res.scalars().all():
        key = f"notification:{n.notification_type}:{n.related_entity_id or n.id}"
        seen_keys.add(key)
        items.append(
            _item(
                item_id=n.id,
                source="notification",
                category=_CATEGORY_BY_TYPE.get(n.notification_type, "system"),
                severity=_severity_for_type(n.notification_type),
                title=n.title,
                message=n.message,
                created_at=_iso(n.created_at) or datetime.utcnow().isoformat(),
                is_read=bool(n.is_read),
                action_tab=_action_tab_for_type(n.notification_type),
            )
        )

    interest_res = await db.execute(
        select(StudentCircleInterestRequest)
        .where(StudentCircleInterestRequest.student_signup_id == student.id)
        .order_by(StudentCircleInterestRequest.updated_at.desc())
        .limit(10)
    )
    for req in interest_res.scalars().all():
        ts = _iso(req.updated_at or req.created_at) or datetime.utcnow().isoformat()
        if req.status == "accepted":
            key = f"circle_interest:accepted:{req.id}"
            if key not in seen_keys:
                items.append(
                    _item(
                        item_id=f"circle-interest-{req.id}",
                        source="circle_interest",
                        category="circle",
                        severity="success",
                        title="Circle leader accepted you",
                        message=req.leader_note or "You are now in a sponsorship circle. Chat and progress are unlocked.",
                        created_at=ts,
                        action_tab="Chat & Kia",
                    )
                )
        elif req.status == "rejected":
            key = f"circle_interest:rejected:{req.id}"
            if key not in seen_keys:
                items.append(
                    _item(
                        item_id=f"circle-interest-{req.id}",
                        source="circle_interest",
                        category="circle",
                        severity="warning",
                        title="Circle request declined",
                        message=req.leader_note or "A leader declined your circle request. You can request another open circle.",
                        created_at=ts,
                        action_tab="Join Circle",
                    )
                )
        elif req.status == "probing":
            items.append(
                _item(
                    item_id=f"circle-probe-{req.id}",
                    source="circle_interest",
                    category="circle",
                    severity="action",
                    title="Leader probe chat active",
                    message="A circle leader is chatting with you during the 7-day probe window. Reply in Join Circle.",
                    created_at=ts,
                    action_tab="Join Circle",
                )
            )
        elif req.status in ("pending_leader", "pending"):
            items.append(
                _item(
                    item_id=f"circle-pending-{req.id}",
                    source="circle_interest",
                    category="circle",
                    severity="info",
                    title="Circle request pending",
                    message="Your sponsorship circle request is with a leader for review.",
                    created_at=ts,
                    action_tab="Join Circle",
                )
            )

    school_student = await resolve_school_student(db, student)
    school_res = await db.execute(
        select(StudentSchoolInterest).where(StudentSchoolInterest.student_signup_id == student.id)
    )
    school_interest = school_res.scalar_one_or_none()

    if school_interest and school_interest.status == "pending_principal" and not school_student:
        items.append(
            _item(
                item_id=f"school-pending-{school_interest.id}",
                source="timeline",
                category="school",
                severity="action",
                title="Waiting for school admission",
                message="Your selected school principal has not admitted you yet.",
                created_at=_iso(school_interest.updated_at or school_interest.created_at) or datetime.utcnow().isoformat(),
                action_tab="Overview",
            )
        )
    elif school_student and f"notification:school_admitted:{school_student.id}" not in seen_keys:
        items.append(
            _item(
                item_id=f"school-admitted-{school_student.id}",
                source="timeline",
                category="school",
                severity="success",
                title="School admission confirmed",
                message="Your partner school admitted you. Progress and circle requests can proceed.",
                created_at=_iso(school_student.updated_at if hasattr(school_student, "updated_at") else None)
                or datetime.utcnow().isoformat(),
                action_tab="My Progress",
            )
        )

    timeline = await build_onboarding_timeline(db, student, school_student=school_student)
    tier = student.login_access_tier or LoginAccessTier.consent_required.value
    if tier == LoginAccessTier.guardian_only.value:
        link_res = await db.execute(
            select(StudentFamilyLink).where(StudentFamilyLink.student_signup_id == student.id)
        )
        link = link_res.scalar_one_or_none()
        parent: Optional[SignupRequest] = None
        if link:
            p_res = await db.execute(select(SignupRequest).where(SignupRequest.id == link.parent_signup_id))
            parent = p_res.scalar_one_or_none()
        if not parent or parent.kyc_status != KycStatus.approved:
            items.append(
                _item(
                    item_id="guardian-kyc-required",
                    source="timeline",
                    category="parent",
                    severity="action",
                    title="Parent verification required",
                    message="Because you are under 15, your parent/guardian must complete verification before circle access unlocks.",
                    created_at=datetime.utcnow().isoformat(),
                    action_tab="Overview",
                )
            )

    if timeline.get("in_circle") is False and timeline.get("unlocked_circle_request"):
        if not any(i["category"] == "circle" and i["severity"] == "success" for i in items):
            items.append(
                _item(
                    item_id="circle-request-unlocked",
                    source="timeline",
                    category="circle",
                    severity="action",
                    title="Ready to join a circle",
                    message="School and guardian steps are complete. Request an open sponsorship circle.",
                    created_at=datetime.utcnow().isoformat(),
                    action_tab="Join Circle",
                )
            )

    if timeline.get("unlocked_dashboard") and not timeline.get("in_circle"):
        items.append(
            _item(
                item_id="chat-locked",
                source="timeline",
                category="chat",
                severity="info",
                title="Circle chat locked",
                message="Join a sponsorship circle to unlock live chat with your supporters.",
                created_at=datetime.utcnow().isoformat(),
                action_tab="Join Circle",
            )
        )

    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    items = items[:limit]
    unread_count = sum(1 for i in items if not i.get("is_read"))

    return {
        "items": items,
        "unread_count": unread_count,
        "total": len(items),
    }
