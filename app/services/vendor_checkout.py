"""Shared marketplace checkout (used by vendor router and leader cart approval)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.microservices.vendor.models import VendorOrder, VendorProduct, VendorPromotion, OrderStatus
from app.microservices.vendor.schemas import CartCheckoutRequest, OrderCreate, OrderOut
from app.models.signup import SignupRequest


async def execute_cart_checkout(
    db: AsyncSession,
    body: CartCheckoutRequest,
    buyer: SignupRequest,
) -> List[OrderOut]:
    from app.services.student_circle_privacy import checkout_buyer_display_name

    now = datetime.now(timezone.utc)
    orders: list[VendorOrder] = []
    buyer_label = await checkout_buyer_display_name(
        db, buyer, order_type=body.order_type or "student"
    )

    for item in body.items:
        p_res = await db.execute(select(VendorProduct).where(VendorProduct.id == item.product_id))
        product = p_res.scalar_one_or_none()
        if not product:
            continue

        promo_q = select(VendorPromotion).where(
            VendorPromotion.vendor_id == item.vendor_id,
            VendorPromotion.is_active == True,
            VendorPromotion.start_date <= now,
            VendorPromotion.end_date >= now,
        )
        promo_res = await db.execute(promo_q)
        active_promos = promo_res.scalars().all()

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
            applies = promo.scope == "all" or (
                promo.target_product_ids
                and str(product.id) in promo.target_product_ids.split(",")
            )
            if applies and promo.discount_percentage > best_discount:
                best_discount = promo.discount_percentage
                applied_promo_id = promo.id

        base_price = product.price
        if body.order_type == "student" and product.student_price:
            base_price = product.student_price

        unit_price = float(base_price)
        discount_amount = 0.0
        if best_discount > 0:
            discount_per_unit = unit_price * (best_discount / 100)
            discount_amount = discount_per_unit * item.quantity
            unit_price = unit_price - discount_per_unit

        order = VendorOrder(
            vendor_id=item.vendor_id,
            product_id=item.product_id,
            buyer_id=buyer.id,
            buyer_name=buyer_label,
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

        from app.models.notification import Notification

        db.add(
            Notification(
                recipient_id=item.vendor_id,
                recipient_type="user",
                notification_type="new_order",
                title="New Order Received",
                message=f"You have received a new order for {product.name}.",
                related_entity_id=order.id,
                related_entity_type="order",
            )
        )

    if orders and body.circle_name:
        from app.services.kia_event_briefings import emit_marketplace_transaction

        lines: list[str] = []
        total = 0
        for o in orders:
            prod_result = await db.execute(
                select(VendorProduct.name).where(VendorProduct.id == o.product_id)
            )
            pname = prod_result.scalar_one_or_none() or "Item"
            amt = int(o.total_amount or 0)
            total += amt
            lines.append(f"{pname} ×{o.quantity} — ₹{amt:,}")
        await emit_marketplace_transaction(
            db,
            circle_id=None,
            circle_name=body.circle_name,
            buyer_name=buyer_label,
            order_lines=lines,
            total_inr=total,
            order_type=body.order_type or "student",
        )

    await db.commit()
    for o in orders:
        await db.refresh(o)

    out: list[OrderOut] = []
    for o in orders:
        prod_result = await db.execute(
            select(VendorProduct.name).where(VendorProduct.id == o.product_id)
        )
        product_name = prod_result.scalar_one_or_none()
        order_dict = OrderOut.model_validate(o).model_dump()
        order_dict["product_name"] = product_name
        out.append(OrderOut(**order_dict))
    return out


def order_creates_from_submission_items(items: list[dict]) -> list[OrderCreate]:
    return [
        OrderCreate(
            product_id=str(it["product_id"]),
            quantity=int(it.get("quantity") or 1),
            unit_price=float(it.get("unit_price") or 0),
            total_amount=float(it.get("total_amount") or it.get("unit_price") or 0)
            * int(it.get("quantity") or 1),
            vendor_id=str(it["vendor_id"]),
        )
        for it in items
    ]
