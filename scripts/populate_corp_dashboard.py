import asyncio
import os
from sqlalchemy import text
from sqlalchemy.future import select

# Use the app's real database configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.session import engine, SessionLocal
from app.models.corporate import CorporateProfile

mock_monthly_burn = [
    {"month": "Apr", "amount": 20000}, {"month": "May", "amount": 25000},
    {"month": "Jun", "amount": 30000}, {"month": "Jul", "amount": 20000},
    {"month": "Aug", "amount": 35000}, {"month": "Sep", "amount": 10000},
    {"month": "Oct", "amount": 28000}, {"month": "Nov", "amount": 15000},
    {"month": "Dec", "amount": 40000}, {"month": "Jan", "amount": 22000},
    {"month": "Feb", "amount": 18000}, {"month": "Mar", "amount": 2400},
]
mock_raw_txns = [
    {"date": "1 Apr 25",  "type": "credit",   "description": "Annual CSR commitment — FY26",    "category": "Top-up",       "amount": 1200000, "circle": None,                   "running_balance": 1200000, "reference": "NEFT/TCS/2025/001"},
    {"date": "2 Apr 25",  "type": "debit",    "description": "Ashoka Rising Circle — Q1 tranche","category": "Allocation",   "amount": 20000,   "circle": "Ashoka Rising Circle", "running_balance": 1180000, "reference": "ALLOC/ARC/Q1"},
    {"date": "2 Apr 25",  "type": "debit",    "description": "Udaan Bangalore — Q1 tranche",    "category": "Allocation",   "amount": 7000,    "circle": "Udaan Bangalore",      "running_balance": 1173000, "reference": "ALLOC/UB/Q1"},
    {"date": "5 Apr 25",  "type": "debit",    "description": "Platform fee (10% of commitment)","category": "Platform Fee", "amount": 10000,   "circle": None,                   "running_balance": 1163000, "reference": "FEE/2025/Q1"},
    {"date": "1 Jul 25",  "type": "debit",    "description": "Ashoka Rising Circle — Q2 tranche","category": "Allocation",  "amount": 20000,   "circle": "Ashoka Rising Circle", "running_balance": 1143000, "reference": "ALLOC/ARC/Q2"},
    {"date": "1 Jul 25",  "type": "debit",    "description": "Udaan Bangalore — Q2 tranche",    "category": "Allocation",   "amount": 5500,    "circle": "Udaan Bangalore",      "running_balance": 1137500, "reference": "ALLOC/UB/Q2"},
    {"date": "1 Oct 25",  "type": "debit",    "description": "Ashoka Rising Circle — Q3 tranche","category": "Allocation",  "amount": 10000,   "circle": "Ashoka Rising Circle", "running_balance": 1127500, "reference": "ALLOC/ARC/Q3"},
    {"date": "1 Oct 25",  "type": "debit",    "description": "Udaan Bangalore — Q3 tranche",    "category": "Allocation",   "amount": 6500,    "circle": "Udaan Bangalore",      "running_balance": 1121000, "reference": "ALLOC/UB/Q3"},
    {"date": "24 Nov 25", "type": "interest", "description": "C.C. Escrow interest credited",  "category": "Interest",     "amount": 2400,    "circle": None,                   "running_balance": 1123400, "reference": "INT/2025/NOV"},
    {"date": "1 Mar 26",  "type": "debit",    "description": "Ashoka Rising Circle — Q4 partial","category": "Allocation",  "amount": 2400,    "circle": "Ashoka Rising Circle", "running_balance": 1121000, "reference": "ALLOC/ARC/Q4P"},
]
mock_upcoming = [
    {"circle_name": "Ashoka Rising Circle", "amount": 20000, "due_date": "Apr 1, 2026", "status": "scheduled",        "tranche": "Q1 FY26-27"},
    {"circle_name": "Udaan Bangalore",      "amount": 7500,  "due_date": "Apr 1, 2026", "status": "pending_approval", "tranche": "Q1 FY26-27"},
    {"circle_name": "ZenK Platform Fee",    "amount": 12000, "due_date": "Apr 5, 2026", "status": "scheduled",        "tranche": "Annual Fee"},
]
mock_alerts = [
    {"type": "warning", "message": "₹3,00,000 unallocated — Q4 FY26 allocation deadline is Apr 1, 2026 (30 days away)."},
    {"type": "info", "message": "₹2,400 escrow interest was credited to your account on 24 Nov 2025."},
    {"type": "info", "message": "Annual MCA compliance filing due by Sep 30, 2026. You are currently on track."},
]

async def migrate_and_populate():
    async with engine.begin() as conn:
        try:
            await conn.execute(text('ALTER TABLE "ZENK".corporate_profiles ADD COLUMN IF NOT EXISTS monthly_burn JSONB;'))
            await conn.execute(text('ALTER TABLE "ZENK".corporate_profiles ADD COLUMN IF NOT EXISTS alerts JSONB;'))
            await conn.execute(text('ALTER TABLE "ZENK".corporate_profiles ADD COLUMN IF NOT EXISTS upcoming_disbursements JSONB;'))
            print("Successfully ensured columns exist.")
        except Exception as e:
            print(f"Error adding columns: {e}")
            
    async with SessionLocal() as session:
        result = await session.execute(select(CorporateProfile))
        profiles = result.scalars().all()
        for p in profiles:
            p.monthly_burn = mock_monthly_burn
            p.alerts = mock_alerts
            p.upcoming_disbursements = mock_upcoming
            if not p.transactions:
                p.transactions = mock_raw_txns
        
        await session.commit()
        print(f"Successfully populated {len(profiles)} corporate profiles.")

if __name__ == "__main__":
    asyncio.run(migrate_and_populate())
