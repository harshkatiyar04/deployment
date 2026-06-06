"""Live vendor + school supplier registry for admin (marketplace & education partners)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.microservices.vendor.models import OrderStatus, ProductRequest, RequestStatus, VendorOrder, VendorProduct
from app.models.enums import KycStatus, Persona
from app.models.school import SchoolProfile, SchoolStudent
from app.models.signup import SignupRequest

DELIVERED = (
    OrderStatus.delivered,
    OrderStatus.shipped,
    OrderStatus.processing,
)


def _kyc_value(s: KycStatus | str) -> str:
    return s.value if hasattr(s, "value") else str(s)


def _account_status(kyc: KycStatus, *, is_partner: bool = True) -> str:
    if kyc == KycStatus.approved:
        return "active" if is_partner else "suspended"
    if kyc == KycStatus.pending:
        return "pending"
    return "suspended"


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


async def build_admin_suppliers_registry(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    supplier_kind: Optional[str] = None,
    status: Optional[str] = None,
) -> dict[str, Any]:
    vendors_res = await db.execute(
        select(SignupRequest)
        .where(SignupRequest.persona == Persona.vendor)
        .order_by(SignupRequest.created_at.desc())
    )
    vendors = list(vendors_res.scalars().all())
    vendor_ids = [v.id for v in vendors]

    product_stats: dict[str, tuple[int, int]] = {}
    if vendor_ids:
        ps_res = await db.execute(
            select(
                VendorProduct.vendor_id,
                func.count(VendorProduct.id),
                func.count(VendorProduct.id).filter(VendorProduct.is_active.is_(True)),
            )
            .where(VendorProduct.vendor_id.in_(vendor_ids))
            .group_by(VendorProduct.vendor_id)
        )
        product_stats = {vid: (int(tot), int(active)) for vid, tot, active in ps_res.all()}

    order_stats: dict[str, dict[str, Any]] = {}
    if vendor_ids:
        os_res = await db.execute(
            select(
                VendorOrder.vendor_id,
                func.count(VendorOrder.id),
                func.coalesce(func.sum(VendorOrder.total_amount), 0),
                func.count(VendorOrder.id).filter(VendorOrder.status == OrderStatus.delivered),
                func.coalesce(
                    func.sum(VendorOrder.total_amount).filter(
                        VendorOrder.status.in_(list(DELIVERED))
                    ),
                    0,
                ),
                func.count(VendorOrder.id).filter(VendorOrder.status == OrderStatus.pending),
            )
            .where(VendorOrder.vendor_id.in_(vendor_ids))
            .group_by(VendorOrder.vendor_id)
        )
        for vid, total, gmv, delivered_n, delivered_gmv, pending_n in os_res.all():
            order_stats[vid] = {
                "orders": int(total),
                "gmv_inr": float(gmv),
                "delivered_orders": int(delivered_n),
                "delivered_gmv_inr": float(delivered_gmv),
                "pending_orders": int(pending_n),
            }

    request_stats: dict[str, int] = {}
    if vendor_ids:
        pr_res = await db.execute(
            select(ProductRequest.vendor_id, func.count(ProductRequest.id))
            .where(
                ProductRequest.vendor_id.in_(vendor_ids),
                ProductRequest.status == RequestStatus.pending,
            )
            .group_by(ProductRequest.vendor_id)
        )
        request_stats = {vid: int(n) for vid, n in pr_res.all()}

    schools_res = await db.execute(
        select(SchoolProfile, SignupRequest)
        .join(SignupRequest, SignupRequest.id == SchoolProfile.id)
        .order_by(SchoolProfile.created_at.desc())
    )
    school_rows = schools_res.all()
    school_ids = [p.id for p, _ in school_rows]

    student_stats: dict[str, dict[str, Any]] = {}
    if school_ids:
        st_res = await db.execute(
            select(
                SchoolStudent.school_id,
                func.count(SchoolStudent.id),
                func.avg(SchoolStudent.zqa_score),
                func.avg(SchoolStudent.attendance_pct),
                func.avg(SchoolStudent.avg_score),
                func.count(SchoolStudent.id).filter(SchoolStudent.circle_id.isnot(None)),
                func.coalesce(func.sum(SchoolStudent.zenq_contribution), 0),
            )
            .where(SchoolStudent.school_id.in_(school_ids))
            .group_by(SchoolStudent.school_id)
        )
        for sid, cnt, zqa, att, acad, in_circle, zenq_sum in st_res.all():
            student_stats[sid] = {
                "students": int(cnt),
                "zenq_avg": round(float(zqa), 1) if zqa is not None else None,
                "attendance_avg": round(float(att), 1) if att is not None else None,
                "academic_avg": round(float(acad), 1) if acad is not None else None,
                "circle_enrollments": int(in_circle),
                "zenq_contribution_total": round(float(zenq_sum), 1) if zenq_sum else 0.0,
            }

    items: list[dict[str, Any]] = []

    for v in vendors:
        products_total, products_active = product_stats.get(v.id, (0, 0))
        orders = order_stats.get(v.id, {})
        total_orders = orders.get("orders", 0)
        delivered_orders = orders.get("delivered_orders", 0)
        fulfillment = (
            round((delivered_orders / total_orders) * 100, 1) if total_orders > 0 else None
        )
        items.append(
            {
                "id": v.id,
                "supplier_kind": "vendor",
                "name": v.business_name or v.full_name,
                "email": v.email,
                "contact_name": v.full_name,
                "subtype": v.business_type or "Marketplace vendor",
                "status": _account_status(v.kyc_status),
                "kyc_status": _kyc_value(v.kyc_status),
                "catalogue_count": products_total,
                "active_catalogue": products_active,
                "orders_count": total_orders,
                "pending_orders": orders.get("pending_orders", 0),
                "gmv_inr": orders.get("gmv_inr", 0),
                "delivered_gmv_inr": orders.get("delivered_gmv_inr", 0),
                "fulfillment_pct": fulfillment,
                "zenq_score": None,
                "avg_attendance": None,
                "avg_academic_score": None,
                "reports_pending": None,
                "circle_enrollments": None,
                "zenq_contribution_total": None,
                "product_requests_pending": request_stats.get(v.id, 0),
                "city": v.city,
                "joined_at": _iso(v.created_at),
            }
        )

    for profile, signup in school_rows:
        stats = student_stats.get(profile.id, {})
        zenq = stats.get("zenq_avg")
        if zenq is None and profile.avg_academic_score:
            zenq = round(float(profile.avg_academic_score), 1)
        items.append(
            {
                "id": profile.id,
                "supplier_kind": "school",
                "name": profile.school_name,
                "email": signup.email,
                "contact_name": profile.principal_name,
                "subtype": f"School · {profile.affiliation}",
                "status": _account_status(signup.kyc_status, is_partner=profile.is_partner),
                "kyc_status": _kyc_value(signup.kyc_status),
                "catalogue_count": stats.get("students", profile.total_enrolled or 0),
                "active_catalogue": stats.get("students", profile.total_enrolled or 0),
                "orders_count": stats.get("circle_enrollments", 0),
                "pending_orders": profile.reports_pending or 0,
                "gmv_inr": None,
                "delivered_gmv_inr": None,
                "fulfillment_pct": None,
                "zenq_score": zenq,
                "avg_attendance": stats.get("attendance_avg") or round(float(profile.avg_attendance), 1),
                "avg_academic_score": stats.get("academic_avg") or round(float(profile.avg_academic_score), 1),
                "reports_pending": profile.reports_pending or 0,
                "circle_enrollments": stats.get("circle_enrollments", 0),
                "zenq_contribution_total": stats.get("zenq_contribution_total"),
                "product_requests_pending": 0,
                "city": profile.city,
                "joined_at": _iso(profile.created_at),
            }
        )

    needle = (search or "").strip().lower()
    if needle:
        items = [
            i
            for i in items
            if needle in (i["name"] or "").lower()
            or needle in (i["email"] or "").lower()
            or needle in (i["contact_name"] or "").lower()
            or needle in (i["city"] or "").lower()
        ]

    if supplier_kind and supplier_kind != "all":
        items = [i for i in items if i["supplier_kind"] == supplier_kind]

    if status and status != "all":
        items = [i for i in items if i["status"] == status]

    total_gmv = sum(float(i.get("delivered_gmv_inr") or 0) for i in items if i["supplier_kind"] == "vendor")

    summary = {
        "total": len(items),
        "vendors": sum(1 for i in items if i["supplier_kind"] == "vendor"),
        "schools": sum(1 for i in items if i["supplier_kind"] == "school"),
        "active": sum(1 for i in items if i["status"] == "active"),
        "pending": sum(1 for i in items if i["status"] == "pending"),
        "suspended": sum(1 for i in items if i["status"] == "suspended"),
        "total_delivered_gmv_inr": round(total_gmv, 0),
        "active_products": sum(i.get("active_catalogue") or 0 for i in items if i["supplier_kind"] == "vendor"),
        "school_students": sum(i.get("catalogue_count") or 0 for i in items if i["supplier_kind"] == "school"),
    }

    return {"summary": summary, "suppliers": items}
