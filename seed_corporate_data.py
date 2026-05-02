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
            
            if "corporate2" in user.email.lower():
                company_name = "ICICI Bank"
                company_initials = "ICICI"
            elif "hcl" in user.email.lower():
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
                "brand_color": "#E31E24" if company_initials == "ICICI" else "#004B98",
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
                    {
                        "circle_name": "Ashoka Rising Circle", 
                        "leader": "Dr. Rahul Sharma", 
                        "city": "Mumbai", 
                        "zenq_score": 82, 
                        "rank": 3, 
                        "participation_pct": 78, 
                        "members": 14, 
                        "students": 42, 
                        "monthly_trend": [70, 72, 75, 76, 78, 80, 81, 82, 82, 82, 82, 82], 
                        "status": "active",
                        "kia_insight": "Student milestone (Mar): Maths score improved from 61% to 84% at personal baseline. Circle ranked #3 of 47. On track for Platinum ZenQ by Sep 2026. Your funding directly enabled Term 2 textbooks, science materials, and exam registration.",
                        "zenq_start": 58.0,
                        "fund_utilised_pct": 83,
                        "student_zqa": 84,
                        "allocation_amount": 60000,
                        "allocation_pct": 60,
                        "next_disbursement": "Jun 1, 2026",
                        "color": "#00D4BE",
                        "volunteers": [
                            {"name": "Priya Sharma", "initials": "PS", "hours_per_month": 12.5},
                            {"name": "Rahul Joshi", "initials": "RJ", "hours_per_month": 8.0}
                        ],
                        "milestones": [
                            {"month": "Mar", "event": "Term 2 Textbooks Distributed"},
                            {"month": "Feb", "event": "Science Lab Setup Completed"}
                        ],
                        "predicted_zenq_by_fy_end": 88.0
                    },
                    {
                        "circle_name": "Udaan Bangalore", 
                        "leader": "Ms. Sunita Kumar", 
                        "city": "Bengaluru", 
                        "zenq_score": 78, 
                        "rank": 7, 
                        "participation_pct": 61, 
                        "members": 11, 
                        "students": 33, 
                        "monthly_trend": [62, 64, 66, 68, 70, 72, 74, 75, 76, 77, 78, 78], 
                        "status": "active",
                        "kia_insight": "Circle participation is below average at 61%. Your TCS volunteer Priya Kulkarni is contributing 12 hrs/month. Nominating one more TCS employee as science mentor would lift this circle's ZenQ by an estimated +4 pts and your Corporate ZenQ by +0.8 pts.",
                        "zenq_start": 64.0,
                        "fund_utilised_pct": 71,
                        "student_zqa": 76,
                        "allocation_amount": 20000,
                        "allocation_pct": 20,
                        "next_disbursement": "Jun 1, 2026",
                        "color": "#F6C343",
                        "volunteers": [
                            {"name": "Priya Kulkarni", "initials": "PK", "hours_per_month": 12.0}
                        ],
                        "milestones": [
                            {"month": "Mar", "event": "Mentorship Kickoff"},
                            {"month": "Jan", "event": "Circle Formed"}
                        ],
                        "risk_flag": "Low Participation",
                        "predicted_zenq_by_fy_end": 80.0
                    }
                ],
                "active_this_month": 9,
                "avg_hours_per_employee": 7.0,
                "zenq_lift_from_staff": 8.2,
                "engagement_metrics": [
                    {"label": "Volunteers Active", "value": "12", "delta": "+3 this FY", "trend": "up"},
                    {"label": "Hours Contributed", "value": "84 hrs", "delta": "This FY", "trend": "up"},
                    {"label": "Employee Circles Formed", "value": "2", "delta": "Co-funded by TCS", "trend": "up"},
                    {"label": "ZenQ Lift from Staff", "value": "+8.2", "delta": "Added to Corp ZenQ", "trend": "up"}
                ],
                "volunteers": [
                    {"name": "Priya Kulkarni", "initials": "PK", "department": "Engineering", "hours": 12, "impact_score": 94, "circle": "Ashoka Rising Circle", "zenq_contribution": 0.3, "badge": "gold"},
                    {"name": "Rahul Joshi", "initials": "RJ", "department": "Sales", "hours": 10, "impact_score": 88, "circle": "Udaan Bangalore", "zenq_contribution": 0.2, "badge": "silver"},
                    {"name": "Sonal Mehta", "initials": "SM", "department": "HR", "hours": 8, "impact_score": 84, "circle": "Ashoka Rising", "zenq_contribution": 0.6, "badge": "bronze"},
                    {"name": "Vikram Nair", "initials": "VN", "department": "Finance", "hours": 7, "impact_score": 79, "circle": "Udaan Bangalore", "zenq_contribution": 0.3}
                ],
                "top_contributors": [
                    {"name": "Priya Kulkarni", "initials": "PK", "department": "Engineering", "hours": 12, "impact_score": 94, "circle": "Ashoka Rising Circle", "zenq_contribution": 0.3, "badge": "gold"},
                    {"name": "Rahul Joshi", "initials": "RJ", "department": "Sales", "hours": 10, "impact_score": 88, "circle": "Udaan Bangalore", "zenq_contribution": 0.2, "badge": "silver"},
                    {"name": "Sonal Mehta", "initials": "SM", "department": "HR", "hours": 8, "impact_score": 84, "circle": "Ashoka Rising", "zenq_contribution": 0.6, "badge": "bronze"},
                    {"name": "Vikram Nair", "initials": "VN", "department": "Finance", "hours": 7, "impact_score": 79, "circle": "Udaan Bangalore", "zenq_contribution": 0.3},
                    {"name": "Asha Reddy", "initials": "AR", "department": "Product", "hours": 6, "impact_score": 76}
                ],
                "employee_circles": [
                    {"name": "TCS Mumbai Staff Circle", "employees": 5, "company_match": 20000, "zenq": 74, "rank": 7, "fund": 56000},
                    {"name": "TCS Bengaluru Tech Circle", "employees": 8, "company_match": 15000, "zenq": 68, "rank": 9, "fund": 42000}
                ],
                "engagement_schemes": [
                    {
                        "icon": "🤝", "title": "1:1 Contribution matching",
                        "description": "TCS matches every employee personal contribution to a ZenK circle up to ₹10,000 per employee per year. Doubles the employee's impact and is counted toward TCS Corporate ZenQ.",
                        "participants": 34, "total_matched": 340000, "zenq_uplift": 4.2, "status": "Active"
                    },
                    {
                        "icon": "🕐", "title": "Paid volunteer hours (4 hrs/month)",
                        "description": "TCS employees receive 4 paid hours per month to volunteer as tutors or mentors. Hours logged on ZenK platform count toward TCS's Corporate ZenQ impact score.",
                        "participants": 2400, "total_matched": None, "zenq_uplift": None, "status": "Active",
                        "extra": "Active: 12 | Hours logged: 84 | Target: 500 employees"
                    },
                    {
                        "icon": "🏫", "title": "Employee Circle Formation Grant",
                        "description": "Employees who form a Sponsor Circle receive a ₹60,000 seed grant from TCS Foundation. The circle is added to TCS's Corporate ZenQ tally, amplifying the company's impact score.",
                        "participants": 2, "total_matched": None, "zenq_uplift": 4.2, "status": "Active",
                        "extra": "Circles formed: 2 | Target FY25: 10 circles"
                    }
                ],
                "department_breakdown": [
                    {"department": "Engineering", "employees": 450, "active": 5, "hours": 36},
                    {"department": "HR", "employees": 120, "active": 2, "hours": 14},
                    {"department": "Finance", "employees": 200, "active": 2, "hours": 12},
                    {"department": "Product", "employees": 180, "active": 1, "hours": 8},
                    {"department": "Sales", "employees": 300, "active": 2, "hours": 14}
                ],
                "monthly_hours": [
                    {"month": "Apr", "hours": 32}, {"month": "May", "hours": 38},
                    {"month": "Jun", "hours": 41}, {"month": "Jul", "hours": 44},
                    {"month": "Aug", "hours": 48}, {"month": "Sep", "hours": 52},
                    {"month": "Oct", "hours": 58}, {"month": "Nov", "hours": 62},
                    {"month": "Dec", "hours": 65}, {"month": "Jan", "hours": 70},
                    {"month": "Feb", "hours": 74}, {"month": "Mar", "hours": 84}
                ],
                "kia_engagement_insight": "Your Engineering team leads with 5 active volunteers and 36 hrs/month, but represents only 1.1% of the department. Nominating 3 more engineers as mentors could lift your Corporate ZenQ by an estimated +2.4 pts and unlock the Platinum Engagement tier.",
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
