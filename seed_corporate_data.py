import asyncio
import logging
from sqlalchemy import select
from app.db.session import engine
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.signup import SignupRequest
from app.models.corporate import CorporateProfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed():
    async with AsyncSession(engine) as db:
        logger.info("Checking for corporate users...")
        stmt = select(SignupRequest).where(SignupRequest.email.like("%corporate%"))
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        if not users:
            logger.info("No corporate users found.")
            return
            
        for user in users:
            # Check if profile exists
            p_stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
            p_res = await db.execute(p_stmt)
            profile = p_res.scalar_one_or_none()
            
            if "corporate2" in user.email.lower() or "hcl" in user.email.lower():
                company_name = "HCL Foundation"
                company_initials = "HCL"
            else:
                company_name = "TCS Foundation"
                company_initials = "TCS"
                
            default_data = {
                "id": user.id,
                "company_name": company_name,
                "company_initials": company_initials,
                "hq_city": "Mumbai" if company_initials == "TCS" else "Noida",
                "total_csr_deployed": 100000,
                "unallocated": 20000,
                "fy_label": "FY 2025-26",
                "badges": [
                    {"label": "Impact Leader — Gold Tier", "color": "gold"},
                    {"label": "ZenK Certified Partner", "color": "teal"},
                ],
                "zenq_trend": [
                    {"month": "Apr", "corporate_score": 58, "national_avg": 72},
                    {"month": "May", "corporate_score": 61, "national_avg": 72},
                    {"month": "Jun", "corporate_score": 64, "national_avg": 72},
                    {"month": "Jul", "corporate_score": 67, "national_avg": 72},
                    {"month": "Aug", "corporate_score": 69, "national_avg": 72},
                    {"month": "Sep", "corporate_score": 71, "national_avg": 72},
                    {"month": "Oct", "corporate_score": 73, "national_avg": 72},
                    {"month": "Nov", "corporate_score": 74, "national_avg": 72},
                    {"month": "Dec", "corporate_score": 75, "national_avg": 72},
                    {"month": "Jan", "corporate_score": 76, "national_avg": 72},
                    {"month": "Feb", "corporate_score": 77, "national_avg": 72},
                    {"month": "Mar", "corporate_score": 78.4, "national_avg": 72},
                ],
                "circle_allocations": [
                    {"circle_name": "Ashoka Rising Circle", "leader_name": "Dr. Rahul Sharma", "leader_city": "Mumbai", "allocation_pct": 60, "amount": 60000, "zenq_score": 82, "status": "active", "color": "#00D4BE"},
                    {"circle_name": "Udaan Bangalore", "leader_name": "Ms. Sunita Kumar", "leader_city": "Bengaluru", "allocation_pct": 20, "amount": 20000, "zenq_score": 78, "status": "active", "color": "#F6C343"},
                    {"circle_name": "Unallocated", "leader_name": "—", "leader_city": "—", "allocation_pct": 20, "amount": 20000, "zenq_score": None, "status": "pending", "color": "#4e4635"}
                ],
                "circle_performance": [
                    {"circle_name": "Ashoka Rising Circle", "leader": "Dr. Rahul Sharma", "city": "Mumbai", "zenq_score": 82, "rank": 3, "participation_pct": 78, "members": 14, "students": 42, "monthly_trend": [70, 72, 75, 76, 78, 80, 81, 82, 82, 82, 82, 82], "status": "active"},
                    {"circle_name": "Udaan Bangalore", "leader": "Ms. Sunita Kumar", "city": "Bengaluru", "zenq_score": 78, "rank": 7, "participation_pct": 65, "members": 11, "students": 33, "monthly_trend": [62, 64, 66, 68, 70, 72, 74, 75, 76, 77, 78, 78], "status": "active"}
                ],
                "engagement_metrics": [
                    {"label": "Total Enrolled", "value": "12", "delta": "+3 this FY", "trend": "up"},
                    {"label": "Active This Month", "value": "9", "delta": "+2 vs last month", "trend": "up"},
                    {"label": "Avg Hours/Employee", "value": "6.5h", "delta": "-0.5h vs last month", "trend": "down"},
                    {"label": "Volunteer Hours Total", "value": "78h", "delta": "+12h this month", "trend": "up"}
                ],
                "top_contributors": [
                    {"name": "Priya Sharma", "initials": "PS", "department": "Engineering", "hours": 14, "impact_score": 92},
                    {"name": "Arjun Mehta", "initials": "AM", "department": "HR", "hours": 12, "impact_score": 88},
                    {"name": "Divya Nair", "initials": "DN", "department": "Finance", "hours": 11, "impact_score": 84},
                    {"name": "Rahul Joshi", "initials": "RJ", "department": "Product", "hours": 9, "impact_score": 81},
                    {"name": "Sneha Kapoor", "initials": "SK", "department": "Sales", "hours": 8, "impact_score": 79}
                ],
                "spend_by_category": [
                    {"category": "Student Circles", "amount": 80000, "color": "#00D4BE"},
                    {"category": "Platform Fee", "amount": 10000, "color": "#F6C343"},
                    {"category": "Unallocated", "amount": 20000, "color": "#4e4635"}
                ],
                "transactions": [
                    {"date": "Mar 20, 2026", "description": "Ashoka Rising Circle — Q4 Tranche", "category": "Circle Fund", "amount": 15000, "type": "debit", "circle": "Ashoka Rising Circle"},
                    {"date": "Mar 10, 2026", "description": "Udaan Bangalore — Q4 Tranche", "category": "Circle Fund", "amount": 5000, "type": "debit", "circle": "Udaan Bangalore"},
                    {"date": "Feb 28, 2026", "description": "CSR Disbursement", "category": "Inflow", "amount": 100000, "type": "credit"},
                    {"date": "Jan 15, 2026", "description": "Platform Service Fee Q3", "category": "Platform Fee", "amount": 2500, "type": "debit"},
                    {"date": "Dec 20, 2025", "description": "Ashoka Rising Circle — Q3 Tranche", "category": "Circle Fund", "amount": 15000, "type": "debit", "circle": "Ashoka Rising Circle"},
                    {"date": "Dec 10, 2025", "description": "Udaan Bangalore — Q3 Tranche", "category": "Circle Fund", "amount": 5000, "type": "debit", "circle": "Udaan Bangalore"},
                    {"date": "Nov 5, 2025", "description": "Ashoka Rising Circle — Q2 Tranche", "category": "Circle Fund", "amount": 15000, "type": "debit", "circle": "Ashoka Rising Circle"},
                    {"date": "Oct 1, 2025", "description": "Platform Service Fee Q2", "category": "Platform Fee", "amount": 2500, "type": "debit"}
                ]
            }
            
            if profile:
                logger.info(f"Updating profile for {user.email}")
                for k, v in default_data.items():
                    setattr(profile, k, v)
            else:
                logger.info(f"Creating new profile for {user.email}")
                profile = CorporateProfile(**default_data)
                db.add(profile)
                
        await db.commit()
        logger.info("Seed complete.")

if __name__ == "__main__":
    asyncio.run(seed())
