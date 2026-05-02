"""
Kia AI Corporate CSR Advisor Service
====================================
Tailored logic for the Corporate Dashboard. Kia acts as a CSR Advisor here,
referencing corporate budgets, allocations, and engagement stats.
"""
from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.services.kia import _call_llm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Corporate Constitution & Prompt
# ---------------------------------------------------------------------------

_CORPORATE_CONSTITUTION = """You are Kia, ZenK's premier Corporate CSR Advisor.
You are assisting a corporate executive (e.g. CSR Lead or Chairperson) with their CSR strategy and portfolio.
Your tone should be professional, insightful, and strategic.

RULES:
1. Always base your recommendations on the "Corporate Context" provided.
2. If the user asks about their budget, use the EXACT numbers from the context.
3. Suggest ways to improve their Corporate ZenQ score (e.g. engaging more employees, funding high-performing circles).
4. Never assume you are talking to a student or an individual sponsor.
5. Keep answers concise but data-driven.
"""

def _build_corporate_system_prompt(user_context: dict) -> str:
    """Build the full system prompt with corporate context."""
    prompt = _CORPORATE_CONSTITUTION + "\n\n"

    if user_context:
        prompt += "--- CORPORATE CONTEXT ---\n"
        for k, v in user_context.items():
            prompt += f"- {k.replace('_', ' ').title()}: {v}\n"
        prompt += "-------------------------\n"
    else:
        prompt += "--- CORPORATE CONTEXT ---\nNo specific context available.\n-------------------------\n"

    return prompt

# ---------------------------------------------------------------------------
# Mock Corporate Context (Mirroring router.py data)
# ---------------------------------------------------------------------------

from sqlalchemy import select
from app.models.corporate import CorporateProfile

async def fetch_corporate_context(user_id: str, email: str, db: AsyncSession) -> dict:
    """Fetch corporate metrics from the persistent database storage."""
    stmt = select(CorporateProfile).where(CorporateProfile.id == user_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if profile:
        return {
            "company_name": profile.company_name,
            "corporate_zenq": profile.corporate_zenq,
            "total_csr_deployed": profile.total_csr_deployed,
            "circles_funded": profile.circles_funded,
            "employees_engaged": profile.employees_engaged,
            "unallocated_budget": profile.unallocated,
            "fy_label": profile.fy_label,
            "top_performing_circle": "Noida Tech Circle (ZenQ 92)" if "HCL" in profile.company_initials else "Vasundhara Circle (ZenQ 96)",
            "needs_attention": f"Unallocated budget of ₹{profile.unallocated} could fund a new circle. Employee engagement is low at {profile.employees_engaged}."
        }
        
    # Fallback mock in case lazy provisioning hasn't run
    return {
        "company_name": "Corporate Partner",
        "corporate_zenq": 78.4,
        "total_csr_deployed": 100000,
        "circles_funded": 3,
        "employees_engaged": 12,
        "unallocated_budget": 20000,
        "fy_label": "FY 2025-26",
        "top_performing_circle": "Impact Circle",
        "needs_attention": "Low employee engagement"
    }

# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

async def generate_corporate_response(trigger_message: str, user_context: dict) -> Optional[str]:
    """Generate a response from Kia for the corporate dashboard."""
    try:
        system_prompt = _build_corporate_system_prompt(user_context)
        
        return await _call_llm(
            system_prompt=system_prompt,
            user_message=trigger_message,
        )
    except Exception as e:
        logger.error(f"corporate_kia: Error generating response: {e}")
        return None
