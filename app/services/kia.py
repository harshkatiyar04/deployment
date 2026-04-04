"""
Kia AI Bot Service — Mentorship Assistant
Powered by Gemini 1.5 Flash.
"""
import logging
import json
import asyncio
from typing import List, Optional
from app.core.settings import settings

logger = logging.getLogger(__name__)

# --- KIA SYSTEM PROMPT ---
KIA_SYSTEM_PROMPT = """You are Kia, the Career Mentor AI for ZENK Impact. 
Your goal is to guide students towards their educational and career milestones.

RULES:
1. Be encouraging, professional, and empathetic.
2. Provide actionable advice.
3. If you suggest something specific, prefix it with "Kia suggests: " (all caps not needed, but clear).
4. Keep responses concise (under 3 paragraphs).
5. Focus on mentorship, career guidance, and academic support.
6. Do not provide legal, medical, or financial advice.
7. If a user is disrespectful, stay professional but firm.

FORMATTING:
Use plain text. If you want to highlight a suggestion, put it on a new line starting with "Kia suggests: ".
Example:
"Great progress on your maths score! To keep the momentum going,
Kia suggests: Join the advanced algebra workshop this Saturday."
"""

_gemini_client = None

def _get_gemini_client():
    """Lazy-load Gemini client."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    try:
        api_key = settings.gemini_api_key
        if not api_key:
            return None

        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
        return _gemini_client
    except Exception as exc:
        logger.warning("Gemini SDK unavailable for Kia: %s", exc)
        return None

async def generate_kia_response(message_text: str, history: Optional[List[dict]] = None) -> Optional[str]:
    """Generate a mentorship response from Kia."""
    client = _get_gemini_client()
    if not client:
        return None

    try:
        # Construct prompt with basic context if provided
        prompt = f"User said: \"{message_text}\"\n\nGenerate your mentorship response as Kia."
        
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-1.5-flash",
            contents=prompt,
            config={"system_instruction": KIA_SYSTEM_PROMPT, "temperature": 0.7}
        )
        
        if not response or not response.text:
            return None
            
        return response.text.strip()
    except Exception as exc:
        logger.error("Kia AI generation failed: %s", exc)
        return None
