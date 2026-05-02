import asyncio
from app.db.session import engine
from sqlalchemy import text

async def seed_goals():
    async with engine.begin() as conn:
        await conn.execute(text('''
            UPDATE "ZENK"."corporate_profiles"
            SET corporate_goals = '[{"id": 1, "title": "Fund 5 circles by Q2", "target_value": 5, "current_value": 3, "unit": "circles", "status": "on_track"}, {"id": 2, "title": "Engage 50 Employees in Volunteering", "target_value": 50, "current_value": 12, "unit": "employees", "status": "at_risk"}]'::jsonb
            WHERE corporate_goals = '[]'::jsonb OR corporate_goals IS NULL;
        '''))
        print("Goals seeded successfully.")

asyncio.run(seed_goals())
