import asyncio
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import sys

# Add the root directory to sys.path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from app.db.session import SessionLocal
from app.models.signup import SignupRequest
from app.models.enums import Persona
from app.microservices.vendor.models import (
    VendorProduct, VendorOrder, VendorPromotion, ProductRequest, 
    OrderStatus, RequestStatus, RequestPriority
)

async def seed_production_data():
    db = SessionLocal()
    try:
        print("Starting Production Seed...")
        
        # 1. Find or Create Vendor User
        vendor_email = "vendor@zenk"
        res = await db.execute(select(SignupRequest).where(SignupRequest.email == vendor_email))
        vendor = res.scalar_one_or_none()
        
        if not vendor:
            print(f"Creating vendor user: {vendor_email}")
            vendor = SignupRequest(
                id=str(uuid4()),
                email=vendor_email,
                full_name="Aman Kumar",
                password_hash="hashed_password_here", # Not used for this demo bypass
                persona=Persona.vendor,
                is_approved=True
            )
            db.add(vendor)
            await db.commit()
            await db.refresh(vendor)
        
        vendor_id = vendor.id
        print(f"Using Vendor ID: {vendor_id}")

        # 2. Clear existing products/orders to avoid duplicates (Optional)
        # await db.execute(delete(VendorOrder).where(VendorOrder.vendor_id == vendor_id))
        # await db.execute(delete(VendorProduct).where(VendorProduct.vendor_id == vendor_id))
        # await db.commit()

        # 3. Seed Products
        products_data = [
            {"name": "Premium Stationery Pack", "category": "Stationery", "price": 450.0, "mrp": 599.0, "student_price": 350.0},
            {"name": "Class 9 Maths (NCERT)", "category": "Books", "price": 220.0, "mrp": 250.0, "student_price": 180.0},
            {"name": "Scientific Calculator", "category": "Electronics", "price": 850.0, "mrp": 1200.0, "student_price": 750.0},
            {"name": "Ergonomic Study Lamp", "category": "Furniture", "price": 1200.0, "mrp": 1800.0, "student_price": 999.0},
            {"name": "Drawing Kit (Artist Grade)", "category": "Arts", "price": 550.0, "mrp": 750.0, "student_price": 450.0},
        ]

        products = []
        for p_in in products_data:
            # Check if exists
            res = await db.execute(select(VendorProduct).where(VendorProduct.name == p_in["name"], VendorProduct.vendor_id == vendor_id))
            if not res.scalar_one_or_none():
                p = VendorProduct(
                    id=str(uuid4()),
                    vendor_id=vendor_id,
                    name=p_in["name"],
                    category=p_in["category"],
                    description=f"High quality {p_in['name']} for students and professionals.",
                    price=p_in["price"],
                    mrp=p_in["mrp"],
                    student_price=p_in["student_price"],
                    student_discount=25,
                    member_discount=10,
                    stock_quantity=50,
                    is_active=True
                )
                db.add(p)
                products.append(p)
        
        await db.commit()
        print(f"Seeded {len(products)} products.")

        # 4. Seed Orders (To show revenue and stats)
        # We need at least one product to link orders to
        res = await db.execute(select(VendorProduct).where(VendorProduct.vendor_id == vendor_id))
        all_prods = res.scalars().all()
        
        if all_prods:
            order_templates = [
                {"status": OrderStatus.delivered, "days_ago": 2, "amount": 450.0},
                {"status": OrderStatus.delivered, "days_ago": 5, "amount": 220.0},
                {"status": OrderStatus.pending, "days_ago": 1, "amount": 850.0},
                {"status": OrderStatus.processing, "days_ago": 0, "amount": 1200.0},
                {"status": OrderStatus.delivered, "days_ago": 10, "amount": 550.0},
            ]

            for o_in in order_templates:
                order = VendorOrder(
                    id=str(uuid4()),
                    product_id=all_prods[0].id,
                    vendor_id=vendor_id,
                    buyer_name="Test Student",
                    circle_name="Ashoka Rising",
                    quantity=1,
                    unit_price=o_in["amount"],
                    total_amount=o_in["amount"],
                    status=o_in["status"],
                    created_at=datetime.now(timezone.utc) - timedelta(days=o_in["days_ago"])
                )
                db.add(order)
            
            await db.commit()
            print("Seeded 5 orders.")

        print("Production Seed Complete!")

    except Exception as e:
        print(f"Error during seed: {e}")
        await db.rollback()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(seed_production_data())
