import asyncio
from sqlalchemy import text
from app.db.session import engine

SQL = """
ALTER TABLE "ZENK".corporate_profiles
ADD COLUMN IF NOT EXISTS volunteers JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS employee_circles JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS engagement_schemes JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS department_breakdown JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS monthly_hours JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS kia_engagement_insight TEXT,
ADD COLUMN IF NOT EXISTS active_this_month INTEGER,
ADD COLUMN IF NOT EXISTS avg_hours_per_employee FLOAT,
ADD COLUMN IF NOT EXISTS zenq_lift_from_staff FLOAT
"""

async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text(SQL))
    print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
