"""Admin supplier registry — vendors + school partners (admin API key required)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.routers.admin_kyc import _signup_full_details
from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.models.signup import SignupRequest
from app.schemas.signup import FullSignupDetails
from app.services.admin_suppliers_registry import build_admin_suppliers_registry

router = APIRouter(
    prefix="/admin/suppliers",
    tags=["admin-suppliers"],
    dependencies=[Depends(require_admin_api_key)],
)


class AdminSupplierSummaryOut(BaseModel):
    total: int
    vendors: int
    schools: int
    active: int
    pending: int
    suspended: int
    total_delivered_gmv_inr: float
    active_products: int
    school_students: int


class AdminSupplierOut(BaseModel):
    id: str
    supplier_kind: str
    name: str
    email: str
    contact_name: str
    subtype: str
    status: str
    kyc_status: str
    catalogue_count: int
    active_catalogue: int
    orders_count: int
    pending_orders: int
    gmv_inr: Optional[float] = None
    delivered_gmv_inr: Optional[float] = None
    fulfillment_pct: Optional[float] = None
    zenq_score: Optional[float] = None
    avg_attendance: Optional[float] = None
    avg_academic_score: Optional[float] = None
    reports_pending: Optional[int] = None
    circle_enrollments: Optional[int] = None
    zenq_contribution_total: Optional[float] = None
    product_requests_pending: int = 0
    city: Optional[str] = None
    joined_at: Optional[str] = None


class AdminSuppliersRegistryOut(BaseModel):
    summary: AdminSupplierSummaryOut
    suppliers: list[AdminSupplierOut]


@router.get("", response_model=AdminSuppliersRegistryOut)
async def list_admin_suppliers(
    search: Optional[str] = Query(None, max_length=200),
    kind: Optional[str] = Query(None, description="vendor | school | all"),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await build_admin_suppliers_registry(
        db, search=search, supplier_kind=kind, status=status
    )
    return AdminSuppliersRegistryOut(**data)


class AdminSupplierDetailOut(BaseModel):
    supplier: AdminSupplierOut
    signup: FullSignupDetails
    thread_id: Optional[str] = None


@router.get("/{supplier_id}", response_model=AdminSupplierDetailOut)
async def get_admin_supplier_detail(supplier_id: str, db: AsyncSession = Depends(get_db)):
    data = await build_admin_suppliers_registry(db)
    supplier = next((s for s in data["suppliers"] if s["id"] == supplier_id), None)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    res = await db.execute(
        select(SignupRequest)
        .options(selectinload(SignupRequest.documents))
        .where(SignupRequest.id == supplier_id)
    )
    signup = res.scalar_one_or_none()
    if not signup:
        raise HTTPException(status_code=404, detail="Signup record not found")

    from app.services.admin_support_chat import get_or_create_thread

    thread = await get_or_create_thread(db, supplier_id)
    await db.commit()

    return AdminSupplierDetailOut(
        supplier=AdminSupplierOut(**supplier),
        signup=_signup_full_details(signup),
        thread_id=thread.id,
    )
