"""Standalone: run migration 004 to add 'corporate' to persona_enum, then seed corporate user."""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, select
from app.db.session import SessionLocal, engine
from app.models.signup import SignupRequest
from app.models.enums import KycStatus
from app.core.security import hash_password


async def main():
    # Step 1: ALTER TYPE — must run outside a transaction
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TYPE \"ZENK\".persona_enum ADD VALUE IF NOT EXISTS 'corporate'"))
            print("[Migration] OK: Added 'corporate' to persona_enum")
        except Exception as e:
            print(f"[Migration] Note: {e}")

    # Step 2: Seed user
    async with SessionLocal() as session:
        result = await session.execute(
            select(SignupRequest).where(SignupRequest.email == 'corporate@zenk')
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("[Seed] corporate@zenk already exists. Skipping.")
        else:
            # Use raw SQL insert to bypass enum ORM casting issues after ALTER TYPE
            await session.execute(text("""
                INSERT INTO "ZENK".signup_requests
                  (id, persona, full_name, mobile, email, password_hash,
                   address_line1, address_line2, city, state, pincode, country,
                   sponsor_type, company_name, authorized_signatory_name,
                   authorized_signatory_designation, pan_number, kyc_status,
                   created_at, updated_at)
                VALUES
                  (gen_random_uuid(), 'corporate', 'Vikram Patil', '+91-9800000001',
                   'corporate@zenk', :pwd,
                   'TCS House, Raveline Street', 'Fort', 'Mumbai', 'Maharashtra', '400001', 'India',
                   'company', 'TCS Foundation', 'Vikram Patil', 'CSR Lead', 'AABCT1234Z',
                   'approved', now(), now())
            """), {"pwd": hash_password("corporate123")})
            print("[Seed] OK: corporate@zenk / corporate123 created with kyc_status=approved")

        # HCL Foundation
        result2 = await session.execute(
            select(SignupRequest).where(SignupRequest.email == 'corporate2@zenk')
        )
        existing2 = result2.scalar_one_or_none()

        if existing2:
            print("[Seed] corporate2@zenk already exists. Skipping.")
        else:
            await session.execute(text("""
                INSERT INTO "ZENK".signup_requests
                  (id, persona, full_name, mobile, email, password_hash,
                   address_line1, address_line2, city, state, pincode, country,
                   sponsor_type, company_name, authorized_signatory_name,
                   authorized_signatory_designation, pan_number, kyc_status,
                   created_at, updated_at)
                VALUES
                  (gen_random_uuid(), 'corporate', 'Roshni Nadar', '+91-9800000002',
                   'corporate2@zenk', :pwd,
                   'HCL Technology Hub, Sector 126', 'Noida', 'Delhi NCR', 'Uttar Pradesh', '201304', 'India',
                   'company', 'HCL Foundation', 'Roshni Nadar', 'Chairperson', 'AABCH1234Z',
                   'approved', now(), now())
            """), {"pwd": hash_password("corporate123")})
            print("[Seed] OK: corporate2@zenk / corporate123 created with kyc_status=approved")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
