"""Vendor marketplace API router — full CRUD with RBAC."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import StreamingResponse
import csv
import io
from sqlalchemy import func, select, and_, extract
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.kia import generate_kia_response
from app.services.kia_context import fetch_user_context

from app.core.jwt_auth import get_current_user
from app.db.session import get_db
from app.models.signup import SignupRequest
from app.models.enums import Persona
from app.microservices.vendor.models import (
    VendorProduct,
    VendorOrder,
    ProductRequest,
    OrderStatus,
    RequestStatus,
    VendorSettings,
    VendorPromotion,
    CartItem,
)
from app.microservices.vendor.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductOut,
    OrderOut,
    OrderStatusUpdate,
    OrderCreate,
    CartCheckoutRequest,
    ProductRequestCreate,
    ProductRequestOut,
    ProductRequestStatusUpdate,
    VendorStatsOut,
    VendorSettingsUpdate,
    VendorSettingsOut,
    VendorPromotionCreate,
    VendorPromotionOut,
    NotificationOut,
    CartItemCreate,
    CartItemOut,
)

from pydantic import BaseModel

class DashboardBundleOut(BaseModel):
    stats: VendorStatsOut
    products: list[ProductOut]
    orders: list[OrderOut]
    requests: list[ProductRequestOut]

router = APIRouter(prefix="/vendor", tags=["vendor"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simple in-memory TTL cache for the public marketplace endpoint
# Avoids hammering Neon DB on every page load — refreshes every 5 minutes
# ---------------------------------------------------------------------------
_marketplace_cache: dict = {"data": None, "ts": 0.0}
_CACHE_TTL = 5 * 60  # 5 minutes


# ── Helpers ──────────────────────────────────────────────────────────────────

def _require_vendor(user: SignupRequest) -> None:
    """Raise 403 if the authenticated user is not a vendor."""
    if user.persona != Persona.vendor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only vendor accounts can access this resource",
        )


# ── Dashboard Stats ─────────────────────────────────────────────────────────

@router.get("/stats", response_model=VendorStatsOut)
async def get_vendor_stats(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Aggregated KPI statistics for the vendor dashboard."""
    _require_vendor(user)
    now = datetime.now(timezone.utc)

    # Run scalar/count queries sequentially (SQLAlchemy AsyncSession does not support parallel ops on one connection)
    total_products = (await db.execute(select(func.count()).where(VendorProduct.vendor_id == user.id))).scalar() or 0
    active_products = (await db.execute(select(func.count()).where(
        VendorProduct.vendor_id == user.id, VendorProduct.is_active == True
    ))).scalar() or 0
    total_orders = (await db.execute(select(func.count()).where(VendorOrder.vendor_id == user.id))).scalar() or 0
    total_revenue = (await db.execute(select(func.coalesce(func.sum(VendorOrder.total_amount), 0)).where(
        VendorOrder.vendor_id == user.id, VendorOrder.status == OrderStatus.delivered
    ))).scalar() or 0.0
    pending_orders = (await db.execute(select(func.count()).where(
        VendorOrder.vendor_id == user.id, VendorOrder.status == OrderStatus.pending
    ))).scalar() or 0
    pending_requests = (await db.execute(select(func.count()).where(
        and_(ProductRequest.vendor_id == user.id, ProductRequest.status == RequestStatus.pending)
    ))).scalar() or 0
    orders_this_month = (await db.execute(select(func.count()).where(
        VendorOrder.vendor_id == user.id,
        extract("month", VendorOrder.created_at) == now.month,
        extract("year", VendorOrder.created_at) == now.year,
    ))).scalar() or 0
    revenue_this_month = (await db.execute(select(func.coalesce(func.sum(VendorOrder.total_amount), 0)).where(
        VendorOrder.vendor_id == user.id,
        VendorOrder.status == OrderStatus.delivered,
        extract("month", VendorOrder.created_at) == now.month,
        extract("year", VendorOrder.created_at) == now.year,
    ))).scalar() or 0.0
    
    orders_by_status_query = await db.execute(
        select(VendorOrder.status, func.count())
        .where(VendorOrder.vendor_id == user.id)
        .group_by(VendorOrder.status)
    )
    orders_by_status = {status.value: count for status, count in orders_by_status_query.all()}

    # Revenue Trend (Grouping in Python to support all DB dialects easily)
    all_orders = await db.execute(
        select(VendorOrder.created_at, VendorOrder.total_amount).where(
            VendorOrder.vendor_id == user.id,
            VendorOrder.status == OrderStatus.delivered
        ).order_by(VendorOrder.created_at.asc())
    )
    trend_map = {}
    for row in all_orders.all():
        month_str = row.created_at.strftime("%b %Y")
        trend_map[month_str] = trend_map.get(month_str, 0) + row.total_amount
    
    revenue_trend = [{"date": k, "amount": v} for k, v in trend_map.items()]
    if not revenue_trend:
        revenue_trend = [{"date": now.strftime("%b %Y"), "amount": 0}]

    # Auto-expire promotions and notify vendor
    expired_q = select(VendorPromotion).where(
        VendorPromotion.vendor_id == user.id,
        VendorPromotion.is_active == True,
        VendorPromotion.end_date < now
    )
    expired_res = await db.execute(expired_q)
    expired_promos = expired_res.scalars().all()
    
    if expired_promos:
        from app.models.notification import Notification
        for ep in expired_promos:
            ep.is_active = False
            # Create notification
            notif = Notification(
                recipient_id=user.id,
                recipient_type="user",
                notification_type="promotion_expired",
                title="Promotion Expired",
                message=f"Your promotion '{ep.title}' has expired and is no longer active.",
                related_entity_id=ep.id,
                related_entity_type="promotion"
            )
            db.add(notif)
        await db.commit()

    # Count unread notifications
    from app.models.notification import Notification
    notif_res = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.recipient_id == user.id,
            Notification.is_read == False
        )
    )
    unread_notifications = notif_res.scalar() or 0

    return VendorStatsOut(
        total_products=total_products,
        active_products=active_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        pending_requests=pending_requests,
        orders_this_month=orders_this_month,
        revenue_this_month=revenue_this_month,
        revenue_trend=revenue_trend,
        orders_by_status=orders_by_status,
        unread_notifications=unread_notifications,
    )


@router.get("/dashboard-bundle", response_model=DashboardBundleOut)
async def get_dashboard_bundle(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Fetch stats, products, orders, and requests in a single roundtrip."""
    _require_vendor(user)
    
    # Execute sequentially to avoid asyncpg InterfaceError (one operation at a time on single connection)
    stats = await get_vendor_stats(db=db, user=user)
    products = await list_products(category=None, search=None, limit=50, offset=0, db=db, user=user)
    orders = await list_orders(status_filter=None, limit=50, offset=0, db=db, user=user)
    requests = await list_requests(status_filter=None, limit=50, offset=0, db=db, user=user)
    
    return DashboardBundleOut(
        stats=stats,
        products=products,
        orders=orders,
        requests=requests
    )

# ── Promotions ───────────────────────────────────────────────────────────────

@router.get("/promotions", response_model=list[VendorPromotionOut])
async def list_promotions(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """List all promotions created by the vendor."""
    _require_vendor(user)
    result = await db.execute(
        select(VendorPromotion).where(VendorPromotion.vendor_id == user.id).order_by(VendorPromotion.created_at.desc())
    )
    promos = result.scalars().all()
    now = datetime.now(timezone.utc)
    
    out = []
    for p in promos:
        d = VendorPromotionOut.model_validate(p).model_dump()
        
        # Resolve product names if specific
        names = []
        if p.scope == "specific" and p.target_product_ids:
            ids = p.target_product_ids.split(",")
            prod_res = await db.execute(
                select(VendorProduct.name).where(VendorProduct.id.in_(ids))
            )
            names = prod_res.scalars().all()
        d["target_product_names"] = names
            
        # Calculate hours remaining
        if p.is_active and p.end_date > now:
            diff = p.end_date - now
            d["expires_in_hours"] = int(diff.total_seconds() // 3600)
        else:
            d["expires_in_hours"] = 0
            
        out.append(VendorPromotionOut(**d))
    return out


@router.get("/promotions/log", response_model=list[OrderOut])
async def list_promotion_log(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """List all orders that received a promotion discount."""
    _require_vendor(user)
    q = select(VendorOrder).where(
        VendorOrder.vendor_id == user.id,
        VendorOrder.promotion_id != None
    ).order_by(VendorOrder.created_at.desc())
    
    result = await db.execute(q)
    orders = result.scalars().all()
    
    out = []
    for o in orders:
        prod_result = await db.execute(
            select(VendorProduct.name).where(VendorProduct.id == o.product_id)
        )
        product_name = prod_result.scalar_one_or_none()
        order_dict = OrderOut.model_validate(o).model_dump()
        order_dict["product_name"] = product_name
        out.append(OrderOut(**order_dict))
    return out


@router.delete("/promotions/{promo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_promotion(
    promo_id: str,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Delete (or deactivate) a promotion."""
    _require_vendor(user)
    result = await db.execute(
        select(VendorPromotion).where(
            VendorPromotion.id == promo_id,
            VendorPromotion.vendor_id == user.id
        )
    )
    promo = result.scalar_one_or_none()
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    await db.delete(promo)
    await db.commit()


@router.post("/promotions", response_model=VendorPromotionOut, status_code=status.HTTP_201_CREATED)
async def create_promotion(
    body: VendorPromotionCreate,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Create a new discount campaign for the vendor."""
    _require_vendor(user)
    
    data = body.model_dump()
    if data.get("target_product_ids"):
        data["target_product_ids"] = ",".join(data["target_product_ids"])
    else:
        data["target_product_ids"] = None
        
    promo = VendorPromotion(
        vendor_id=user.id,
        **data
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    logger.info(f"Promotion created: {promo.title} by vendor {user.email}")
    
    # Prepare response to match VendorPromotionOut
    res_d = VendorPromotionOut.model_validate(promo).model_dump()
    
    # Calculate expires_in_hours
    now = datetime.now(timezone.utc)
    if promo.is_active and promo.end_date > now:
        diff = promo.end_date - now
        res_d["expires_in_hours"] = int(diff.total_seconds() // 3600)
    else:
        res_d["expires_in_hours"] = 0
        
    return res_d


# ── Products CRUD ────────────────────────────────────────────────────────────

@router.get("/products", response_model=list[ProductOut])
async def list_products(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """List products for the authenticated vendor with optional filters."""
    _require_vendor(user)
    q = select(VendorProduct).where(VendorProduct.vendor_id == user.id)

    if category:
        q = q.where(VendorProduct.category.ilike(f"%{category}%"))
    if search:
        q = q.where(VendorProduct.name.ilike(f"%{search}%"))

    q = q.order_by(VendorProduct.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    products = result.scalars().all()
    return await _apply_promotions_to_products(db, products)


async def _apply_promotions_to_products(db: AsyncSession, products: list[VendorProduct]) -> list[dict]:
    """Calculate discounted prices based on active promotions for different audiences."""
    now = datetime.now(timezone.utc)
    
    # Fetch all active promotions
    promo_q = select(VendorPromotion).where(
        VendorPromotion.is_active == True,
        VendorPromotion.start_date <= now,
        VendorPromotion.end_date >= now
    )
    promo_res = await db.execute(promo_q)
    active_promos = promo_res.scalars().all()
    
    output = []
    for p in products:
        p_data = ProductOut.model_validate(p).model_dump()
        
        best_member_promo = 0.0
        best_student_promo = 0.0
        promo_title = None
        
        for promo in active_promos:
            if promo.vendor_id == p.vendor_id:
                # Check if promo applies to all or this specific product
                applies = False
                if promo.scope == "all":
                    applies = True
                elif promo.target_product_ids:
                    target_ids = promo.target_product_ids.split(",")
                    if str(p.id) in target_ids:
                        applies = True
                
                if applies:
                    # Update member discount if target includes sponsors
                    if promo.target_audience in ["all", "sponsor"]:
                        if promo.discount_percentage > best_member_promo:
                            best_member_promo = promo.discount_percentage
                            if not promo_title or promo.target_audience == "all":
                                promo_title = promo.title
                    
                    # Update student discount if target includes students
                    if promo.target_audience in ["all", "student"]:
                        if promo.discount_percentage > best_student_promo:
                            best_student_promo = promo.discount_percentage
                            if not promo_title: # Use this title if no member title yet
                                promo_title = promo.title
        
        # Apply Member Promotion
        if best_member_promo > 0:
            p_data["discounted_price"] = round(p.price * (1 - best_member_promo / 100), 2)
            # Update member_discount for display (compounded)
            if p.mrp > 0:
                p_data["member_discount"] = int(round((1 - p_data["discounted_price"] / p.mrp) * 100))
        else:
            p_data["discounted_price"] = p.price
            
        # Apply Student Promotion
        if best_student_promo > 0 and p.student_price:
            p_data["student_price"] = round(p.student_price * (1 - best_student_promo / 100), 2)
            # Update student_discount for display (relative to MRP)
            if p.mrp > 0:
                p_data["student_discount"] = int(round((1 - p_data["student_price"] / p.mrp) * 100))
        
        p_data["active_promotion_title"] = promo_title
        output.append(p_data)
    
    return output


@router.get("/marketplace-products", response_model=list[ProductOut])
@router.get("/marketplace/products", response_model=list[ProductOut])
async def list_marketplace_products(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint to list all active products for the marketplace."""
    # Use cache for the default unfiltered request (most common case)
    is_filtered = bool(search) or (category and category != 'All Items')
    now = time.time()
    
    if not is_filtered and _marketplace_cache["data"] is not None and (now - _marketplace_cache["ts"]) < _CACHE_TTL:
        # Check if we should force a refresh (e.g. if we suspect stale inactive products)
        logger.info("[Cache] Returning cached marketplace products.")
        return _marketplace_cache["data"]

    # CRITICAL: We MUST filter by is_active == True for the public marketplace
    q = select(VendorProduct).where(VendorProduct.is_active == True)

    if category and category != 'All Items':
        q = q.where(VendorProduct.category.ilike(f"%{category}%"))
    if search:
        q = q.where(VendorProduct.name.ilike(f"%{search}%"))

    q = q.order_by(VendorProduct.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    products = result.scalars().all()
    
    output = await _apply_promotions_to_products(db, products)
    
    # Store in cache only for unfiltered requests
    if not is_filtered:
        _marketplace_cache["data"] = output
        _marketplace_cache["ts"] = now
        logger.info(f"[Cache] Updated cache with {len(output)} active products.")
    
    return output


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Add a new product to the vendor's inventory."""
    _require_vendor(user)
    product = VendorProduct(
        vendor_id=user.id,
        **body.model_dump(),
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    logger.info(f"Product created: {product.name} by vendor {user.email}")
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: str,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Update an existing product. Vendor must own the product."""
    _require_vendor(user)
    result = await db.execute(
        select(VendorProduct).where(
            VendorProduct.id == product_id,
            VendorProduct.vendor_id == user.id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    product.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Soft-delete a product by setting is_active to False."""
    _require_vendor(user)
    result = await db.execute(
        select(VendorProduct).where(
            VendorProduct.id == product_id,
            VendorProduct.vendor_id == user.id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    product.updated_at = datetime.now(timezone.utc)
    await db.commit()


# ── Orders ───────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=list[OrderOut])
async def list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """List orders for the authenticated vendor."""
    _require_vendor(user)
    q = (
        select(VendorOrder, VendorProduct.name)
        .join(VendorProduct, VendorOrder.product_id == VendorProduct.id, isouter=True)
        .where(VendorOrder.vendor_id == user.id)
    )

    if status_filter:
        try:
            enum_val = OrderStatus(status_filter)
            q = q.where(VendorOrder.status == enum_val)
        except ValueError:
            pass

    q = q.order_by(VendorOrder.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    rows = result.all()  # Each row is (VendorOrder, product_name)

    out = []
    for order, product_name in rows:
        order_dict = OrderOut.model_validate(order).model_dump()
        order_dict["product_name"] = product_name
        out.append(OrderOut(**order_dict))
    return out


# ── Cart Management ──────────────────────────────────────────────────────────

@router.get("/cart", response_model=list[CartItemOut])
async def get_cart(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Retrieve all items in the user's shopping cart."""
    res = await db.execute(
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.user_id == user.id)
        .order_by(CartItem.created_at.desc())
    )
    return res.scalars().all()


@router.post("/cart", response_model=CartItemOut)
async def add_to_cart(
    item: CartItemCreate,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Add an item to the cart or update quantity if it already exists."""
    # Check if item already exists in the same cart type
    stmt = select(CartItem).options(selectinload(CartItem.product)).where(
        CartItem.user_id == user.id,
        CartItem.product_id == item.product_id,
        CartItem.cart_type == item.cart_type
    )
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        existing.quantity += item.quantity
        existing.comment = item.comment or existing.comment
        await db.commit()
        # No need for refresh here as we already have product loaded
        return existing

    new_item = CartItem(
        user_id=user.id,
        product_id=item.product_id,
        quantity=item.quantity,
        cart_type=item.cart_type,
        comment=item.comment
    )
    db.add(new_item)
    await db.commit()
    
    # Reload with product relationship
    res = await db.execute(
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.id == new_item.id)
    )
    return res.scalar_one()


@router.delete("/cart/{cart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    cart_id: str,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Remove a specific item from the cart."""
    stmt = select(CartItem).where(CartItem.id == cart_id, CartItem.user_id == user.id)
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    await db.delete(item)
    await db.commit()
    return None


@router.delete("/cart", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart_items(
    cart_type: Optional[str] = Query(None, pattern="^(personal|student)$"),
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Clear the user's cart (optionally filtered by type)."""
    from sqlalchemy import delete
    stmt = delete(CartItem).where(CartItem.user_id == user.id)
    if cart_type:
        stmt = stmt.where(CartItem.cart_type == cart_type)
    
    await db.execute(stmt)
    await db.commit()
    return None


@router.post("/orders/checkout", response_model=list[OrderOut], status_code=status.HTTP_201_CREATED)
async def checkout_cart(
    body: CartCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Place multiple orders from a cart checkout, applying active promotions."""
    now = datetime.now(timezone.utc)
    orders = []
    
    for item in body.items:
        # Fetch product to verify price and check for promotions
        p_res = await db.execute(select(VendorProduct).where(VendorProduct.id == item.product_id))
        product = p_res.scalar_one_or_none()
        if not product: continue

        # Check for active promotions
        promo_q = select(VendorPromotion).where(
            VendorPromotion.vendor_id == item.vendor_id,
            VendorPromotion.is_active == True,
            VendorPromotion.start_date <= now,
            VendorPromotion.end_date >= now
        )
        promo_res = await db.execute(promo_q)
        active_promos = promo_res.scalars().all()
        
        # Filter by target audience based on order type
        valid_promos = []
        for p in active_promos:
            if p.target_audience == "all":
                valid_promos.append(p)
            elif p.target_audience == "student" and body.order_type == "student":
                valid_promos.append(p)
            elif p.target_audience == "sponsor" and body.order_type == "personal":
                valid_promos.append(p)
        
        best_discount = 0.0
        applied_promo_id = None
        
        for promo in valid_promos:
            applies = False
            if promo.scope == "all":
                applies = True
            elif promo.target_product_ids:
                if str(product.id) in promo.target_product_ids.split(","):
                    applies = True
            
            if applies and promo.discount_percentage > best_discount:
                best_discount = promo.discount_percentage
                applied_promo_id = promo.id
        
        # Determine base price based on order type
        base_price = product.price
        if body.order_type == "student" and product.student_price:
            base_price = product.student_price
            
        unit_price = base_price
        discount_amount = 0.0
        if best_discount > 0:
            discount_per_unit = unit_price * (best_discount / 100)
            discount_amount = discount_per_unit * item.quantity
            unit_price = unit_price - discount_per_unit

        order = VendorOrder(
            vendor_id=item.vendor_id,
            product_id=item.product_id,
            buyer_id=user.id,
            buyer_name=user.full_name,
            circle_name=body.circle_name,
            quantity=item.quantity,
            unit_price=unit_price,
            total_amount=unit_price * item.quantity,
            discount_amount=discount_amount,
            promotion_id=applied_promo_id,
            delivery_address=body.delivery_address,
            phone_number=body.phone_number,
            order_type=body.order_type,
            status=OrderStatus.pending,
        )
        db.add(order)
        orders.append(order)
        
        # Create notification for vendor
        from app.models.notification import Notification
        notif = Notification(
            recipient_id=item.vendor_id,
            recipient_type="user",
            notification_type="new_order",
            title="New Order Received",
            message=f"You have received a new order for {product.name}.",
            related_entity_id=order.id,
            related_entity_type="order"
        )
        db.add(notif)
    
    await db.commit()
    for o in orders:
        await db.refresh(o)

    out = []
    for o in orders:
        prod_result = await db.execute(
            select(VendorProduct.name).where(VendorProduct.id == o.product_id)
        )
        product_name = prod_result.scalar_one_or_none()
        order_dict = OrderOut.model_validate(o).model_dump()
        order_dict["product_name"] = product_name
        out.append(OrderOut(**order_dict))
    
    return out


@router.get("/my-orders", response_model=list[OrderOut])
async def list_my_orders(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """List orders placed by the current user."""
    q = select(VendorOrder).where(VendorOrder.buyer_id == user.id).order_by(VendorOrder.created_at.desc())
    result = await db.execute(q)
    orders = result.scalars().all()

    out = []
    for o in orders:
        prod_result = await db.execute(
            select(VendorProduct.name).where(VendorProduct.id == o.product_id)
        )
        product_name = prod_result.scalar_one_or_none()
        order_dict = OrderOut.model_validate(o).model_dump()
        order_dict["product_name"] = product_name
        out.append(OrderOut(**order_dict))
    return out


@router.put("/orders/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: str,
    body: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Update the status of an order."""
    _require_vendor(user)
    result = await db.execute(
        select(VendorOrder).where(
            VendorOrder.id == order_id,
            VendorOrder.vendor_id == user.id,
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = body.status
    order.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(order)

    prod_result = await db.execute(
        select(VendorProduct.name).where(VendorProduct.id == order.product_id)
    )
    product_name = prod_result.scalar_one_or_none()
    order_dict = OrderOut.model_validate(order).model_dump()
    order_dict["product_name"] = product_name
    return OrderOut(**order_dict)


# ── Product Requests ─────────────────────────────────────────────────────────

@router.post(
    "/requests/submit",
    response_model=ProductRequestOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_product_request(
    body: ProductRequestCreate,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Submit a product request (typically by a Circle Leader)."""
    req = ProductRequest(
        requester_id=user.id,
        **body.model_dump(),
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    logger.info(f"Product request submitted: '{req.title}' by {user.email}")
    out = ProductRequestOut.model_validate(req).model_dump()
    out["requester_name"] = user.full_name
    return ProductRequestOut(**out)


@router.get("/requests", response_model=list[ProductRequestOut])
async def list_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """List product requests. Vendors see requests assigned to them; others see their own."""
    # Join with SignupRequest to get requester's name in one go
    from app.models.signup import SignupRequest as User
    q = select(ProductRequest, User.full_name).join(User, ProductRequest.requester_id == User.id, isouter=True)

    if user.persona == Persona.vendor:
        q = q.where(
            (ProductRequest.vendor_id == user.id) | (ProductRequest.vendor_id == None)
        )
    else:
        q = q.where(ProductRequest.requester_id == user.id)

    if status_filter:
        try:
            enum_val = RequestStatus(status_filter)
            q = q.where(ProductRequest.status == enum_val)
        except ValueError:
            pass

    q = q.order_by(ProductRequest.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    rows = result.all() # (ProductRequest, requester_name)

    out = []
    for req, requester_name in rows:
        req_dict = ProductRequestOut.model_validate(req).model_dump()
        req_dict["requester_name"] = requester_name
        out.append(ProductRequestOut(**req_dict))
    return out


@router.put("/requests/{request_id}/status", response_model=ProductRequestOut)
async def update_request_status(
    request_id: str,
    body: ProductRequestStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Update a product request's status (vendor accepting/fulfilling)."""
    _require_vendor(user)
    result = await db.execute(
        select(ProductRequest).where(ProductRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    req.status = body.status
    if body.vendor_notes:
        req.vendor_notes = body.vendor_notes
    req.vendor_id = user.id
    req.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(req)

    out = ProductRequestOut.model_validate(req).model_dump()
    user_result = await db.execute(
        select(SignupRequest.full_name).where(SignupRequest.id == req.requester_id)
    )
    out["requester_name"] = user_result.scalar_one_or_none()
    return ProductRequestOut(**out)


# ── Settings ─────────────────────────────────────────────────────────────────

@router.get("/settings", response_model=VendorSettingsOut)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Get the vendor's settings."""
    _require_vendor(user)
    result = await db.execute(
        select(VendorSettings).where(VendorSettings.vendor_id == user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = VendorSettings(vendor_id=user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    # Return settings along with user info
    out = {
        "id": settings.id,
        "vendor_id": settings.vendor_id,
        "email_notifications": settings.email_notifications,
        "sms_alerts": settings.sms_alerts,
        "auto_accept_orders": settings.auto_accept_orders,
        "low_stock_threshold": settings.low_stock_threshold,
        "monthly_revenue_target": settings.monthly_revenue_target,
        "updated_at": settings.updated_at,
        "full_name": user.full_name,
        "business_name": user.business_name
    }
    return out


@router.put("/settings", response_model=VendorSettingsOut)
async def update_settings(
    body: VendorSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Update the vendor's settings."""
    _require_vendor(user)
    result = await db.execute(
        select(VendorSettings).where(VendorSettings.vendor_id == user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = VendorSettings(vendor_id=user.id)
        db.add(settings)

    update_data = body.model_dump(exclude_unset=True)
    
    # Update SignupRequest fields if provided
    if "full_name" in update_data:
        user.full_name = update_data.pop("full_name")
    if "business_name" in update_data:
        user.business_name = update_data.pop("business_name")
    
    # Update VendorSettings fields
    for key, value in update_data.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    
    settings.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(settings)
    
    out = {
        "id": settings.id,
        "vendor_id": settings.vendor_id,
        "email_notifications": settings.email_notifications,
        "sms_alerts": settings.sms_alerts,
        "auto_accept_orders": settings.auto_accept_orders,
        "low_stock_threshold": settings.low_stock_threshold,
        "monthly_revenue_target": settings.monthly_revenue_target,
        "updated_at": settings.updated_at,
        "full_name": user.full_name,
        "business_name": user.business_name
    }
    return out


# ── Bulk Upload ──────────────────────────────────────────────────────────────

@router.post("/bulk-upload")
async def bulk_upload_inventory(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Upload a CSV to bulk create or update products."""
    _require_vendor(user)
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
        
    contents = await file.read()
    decoded = contents.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    
    success_count = 0
    errors = []
    
    for row_idx, row in enumerate(reader, start=1):
        try:
            name = row.get("name")
            category = row.get("category")
            price = float(row.get("price", 0))
            mrp = float(row.get("mrp", 0))
            stock = int(row.get("stock_quantity", 0))
            
            if not name or not category or price <= 0 or mrp <= 0:
                raise ValueError("Missing required fields or invalid price/mrp")
                
            product = VendorProduct(
                vendor_id=user.id,
                name=name,
                category=category,
                price=price,
                mrp=mrp,
                stock_quantity=stock,
                sku=row.get("sku"),
                description=row.get("description"),
            )
            db.add(product)
            success_count += 1
        except Exception as e:
            errors.append(f"Row {row_idx}: {str(e)}")
            
    if success_count > 0:
        await db.commit()
        
    return {
        "message": f"Successfully imported {success_count} products.",
        "success_count": success_count,
        "errors": errors
    }


# ── Reporting ────────────────────────────────────────────────────────────────

@router.get("/report")
async def generate_weekly_report(
    period: str = Query("weekly"),
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Download a CSV report of recent orders (filtered by period)."""
    _require_vendor(user)
    now = datetime.now(timezone.utc)
    
    q = select(VendorOrder).where(VendorOrder.vendor_id == user.id)
    
    if period == "weekly":
        from datetime import timedelta
        week_ago = now - timedelta(days=7)
        q = q.where(VendorOrder.created_at >= week_ago)
    elif period == "monthly":
        from datetime import timedelta
        month_ago = now - timedelta(days=30)
        q = q.where(VendorOrder.created_at >= month_ago)
        
    q = q.order_by(VendorOrder.created_at.desc())
    result = await db.execute(q)
    orders = result.scalars().all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order ID", "Date", "Customer Name", "Product ID", "Quantity", "Unit Price", "Total Amount", "Status"])
    
    for o in orders:
        writer.writerow([
            o.id,
            o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            o.buyer_name,
            o.product_id,
            o.quantity,
            o.unit_price,
            o.total_amount,
            o.status.value,
        ])
        
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=vendor_report_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """List all notifications for the current vendor."""
    from app.models.notification import Notification
    q = select(Notification).where(
        Notification.recipient_id == user.id
    ).order_by(Notification.created_at.desc())
    
    result = await db.execute(q)
    return result.scalars().all()


@router.put("/notifications/{notif_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notif_id: str,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Mark a notification as read."""
    from app.models.notification import Notification
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.recipient_id == user.id
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notif)
    return notif


@router.get("/kia-recommendation")
async def get_kia_marketplace_recommendation(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """
    Generate a personalized recommendation from Kia for the marketplace.
    """
    print(f"FETCHING KIA RECOMMENDATION FOR USER: {user.email}")
    
    # Pre-set fallback in case of any error
    fallback_recommendation = (
        "Based on the current curriculum, I recommend looking at the Class 9 Science Exemplar "
        "and NCERT Maths textbooks. These are foundational for Ananya's upcoming ZQA assessment."
    )
    
    try:
        # 1. Fetch user context
        circle_id = "ashoka-rising" 
        
        try:
            from app.chat.models import CircleMember
            res = await db.execute(select(CircleMember.circle_id).where(CircleMember.user_id == str(user.id)).limit(1))
            real_circle_id = res.scalar()
            if real_circle_id:
                circle_id = real_circle_id
        except Exception:
            pass

        context = await fetch_user_context(str(user.id), circle_id, db, is_leader=True)
        
        # 2. Get some top products from the DB to give Kia more context
        from app.microservices.vendor.models import VendorProduct
        result = await db.execute(select(VendorProduct).limit(10))
        products = result.scalars().all()
        product_list = [f"{p.name} (Category: {p.category}, Student Price: ₹{p.student_price})" for p in products]
        
        # 3. Add products to context
        context["marketplace_products"] = product_list
        
        # 4. Generate response
        prompt = (
            "Generate a single, short, proactive recommendation for the educational marketplace "
            "based on the sponsored student's progress and the circle's budget. "
            "Mention 1-2 specific items from the provided list or category types that would help the student right now. "
            "Keep it under 3 sentences."
        )
        
        recommendation = await generate_kia_response(
            message_text=prompt,
            user_context=context,
            channel="PROACTIVE_TRIGGER"
        )
        
        return {"recommendation": recommendation or fallback_recommendation}
        
    except Exception as e:
        print(f"ERROR IN KIA RECOMMENDATION: {e}")
        return {"recommendation": fallback_recommendation}

