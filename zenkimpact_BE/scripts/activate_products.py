import asyncio
from sqlalchemy import select, update
from app.db.session import SessionLocal
from app.microservices.vendor.models import VendorProduct

async def activate_all():
    async with SessionLocal() as session:
        # Update all products to be active
        q = update(VendorProduct).values(is_active=True)
        result = await session.execute(q)
        await session.commit()
        print(f"✅ Successfully activated products. Rowcount: {result.rowcount}")

if __name__ == "__main__":
    asyncio.run(activate_all())
