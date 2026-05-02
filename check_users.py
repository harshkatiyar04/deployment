import asyncio
from app.db.session import engine
from sqlalchemy import text

async def check():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT email FROM \"ZENK\".signup_requests WHERE persona = 'corporate'"))
        for r in res:
            print(r[0])

if __name__ == "__main__":
    asyncio.run(check())
