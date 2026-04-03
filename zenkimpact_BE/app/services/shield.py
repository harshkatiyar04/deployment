"""
Moderation Service — Two-Layer Hybrid Filtering
Layer 1: Pattern-based fast-pass for PII, slurs, and high-risk phrases.
Layer 2: Contextual intent analysis via LLM.
Layer 3: Safety-net fallback for service outages.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# --- LAYER 1: Core Content Filters ---
INDIAN_MOBILE = re.compile(r'\b[6-9]\d{9}\b')
AADHAAR = re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b')
EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', re.IGNORECASE)
URL = re.compile(
    r'(https?://|www\.|bit\.ly|wa\.me|t\.me|instagram\.com|snapchat\.com|telegram\.me)\S+',
    re.IGNORECASE,
)

TOXICITY_RED = re.compile(
    r'\b(f+u*c*k+|s+h+i+t+|b+i+t+c+h+|a+s+s+h+o+l+e+|c+u+n+t+|d+i+c+k+|p+u+s+s+y+|w+h+o+r+e+|s+l+u+t+|b+a+s+t+a+r+d+|i+d+i+o+t+|s+t+u+p+i+d+'
    r'|l+o+w+l+i+f+e+|s+c+u+m+|m+o+r+o+n+|r+e+t+a+r+d+|d+u+m+b+a+s+s+|n+i+g+g+|f+a+g+|t+r+a+s+h+|l+o+s+e+r+|c+r+e+e+p+|p+e+r+v+e+r+t+'
    r'|f+k+k+)',
    re.IGNORECASE,
)

SELF_HARM_FAST = re.compile(
    r'\b(kill[\s-]*your[\s-]*self|kys|suicide|end[\s-]*my[\s-]*life|want[\s-]*to[\s-]*die|self-?harm|cut[\s-]*my[\s-]*self)', # Removed \b at end
    re.IGNORECASE,
)

SOCIAL_HANDLE = re.compile(
    r'(?:^|[\s,])(?:@|ig:|insta:|snap:|tg:)\s?[\w.]{2,30}',
    re.IGNORECASE,
)

# High-Risk Patterns: Substance Promotion/Engagement
SUBSTANCE_FAST = re.compile(
    r'\b('
    r'lets\s*g+e+t+\s*d+r+u+n+k+|w+a+n+n+a+\s*g+e+t+\s*h+i+g+h+|h+i+t+\s*t+h+e+\s*v+a+p+e+|s+m+o+k+e+\s*w+e+e+d+'
    r'|b+u+y+i+n+g+\s*d+r+u+g+s*|s+e+l+l+\s*m+e+\s*d+r+u+g+s*|t+a+k+e+\s*p+i+l+l+s+|d+r+i+n+k+\s*s+o+m+e+\s*b+e+e+r+'
    r'|l+e+t+s+\s*p+a+r+t+y+\s*w+i+t+h+\s*a+l+c+o+h+o+l+|b+u+y+i+n+g+\s*a+l+c+o+h+o+l+|l+o+o+k+i+n+g+\s*f+o+r+\s*w+e+e+d+'
    r'|d+r+u+g+|d+r+u+u+g+'
    r')\b',
    re.IGNORECASE,
)

GEOPOLITICAL_SAFETY = re.compile(
    r'\b('
    r'israel|palestine|palestin|gaza|hamas|hezbollah|taliban'
    r'|ukraine|russia|crimea|taiwan|north\s*korea|syria'
    r'|afghanistan|iraq|yemen|libya|sudan|myanmar|kashmir'
    r'|zionist|jihad|intifada|genocide|ethnic\s*cleansing|war\s*crime'
    r'|nato|nuclear\s*weapon|terrorism|terrorist|insurgent|extremis'
    r'|modi|trump|biden|putin|netanyahu|zelensky|xi\s*jinping'
    r'|world\s*war|civil\s*war|invasion|missile|drone\s*strike|airstrike'
    r'|ceasefire|occupation|colonialism|war\b|warfare|battle|conflict|combat'
    r')(?:s|ed|ing|er)?\b',
    re.IGNORECASE,
)

VIOLENCE_CONTEXT_SAFETY = re.compile(
    r'(should|will|can|could|would|must|let|if)\s+\w+\s+(attack|invade|bomb|nuke|destroy|kill|fight|strike|conquer|annex|overthrow|assassinate|declare\s*war)',
    re.IGNORECASE,
)

OFF_PLATFORM_HINTS = re.compile(
    r'(whatsapp|telegram|snapchat|insta|connect\s*on|dm\s*me|message\s*me\s*on|hit\s*me\s*up|call\s*me|my\s*number|phone\s*number)',
    re.IGNORECASE,
)

# --- LAYER 2: Gemini LLM Context Moderation ---
SYSTEM_PROMPT = """You are the Moderation Brain for ZENK Impact (Youth Mentorship Platform).

Your task is to protect users while allowing professional and helpful mentorship chat.

STRICT BLOCK RULES:
1. GEOPOLITICAL CONFLICT & POLITICS: BLOCK ongoing wars, military actions, or controversial figures.
   (ALLOW general facts e.g. "Delhi is the capital of India").
2. OFF-PLATFORM INTENT: BLOCK attempts to move to external apps (WhatsApp, Insta, etc.).
3. TOXICITY & DISRESPECT: BLOCK insults or slurs.
4. SUBSTANCE ABUSE: BLOCK PROMOTION, encouragement, or active engagement in substance use (alcohol, tobacco, drugs, vaping).
   (ALLOW professional, incidental, or educational mentions without promotional intent e.g. "Alcohol-based sanitizers", "The chemistry of wine").
5. OFF-TOPIC: BLOCK spam, adverts, or illegal content.
   (ALLOW emojis, polite greetings, and natural conversational fillers as they are part of normal mentorship interaction).

Response Format (JSON ONLY):
{"action": "block", "reason": "off_topic_content"}
{"action": "block", "reason": "toxicity_or_self_harm"}
{"action": "block", "reason": "off_platform_intent"}
{"action": "allow", "reason": null}

CRITICAL: Be extremely sensitive to self-harm and hate speech. BLOCK any content using leetspeak, intentional typos, character repetition, or phonetic similarity to bypass filters (e.g. "fkk offf" = "fuck off", "druug" = "drug"). Look for the INTENDED meaning of the message.
"""

_gemini_client = None

def _get_gemini_client():
    """Lazy-load Gemini client."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    try:
        from app.core.settings import settings
        api_key = settings.gemini_api_key
        if not api_key:
            return None

        from google import genai 
        _gemini_client = genai.Client(api_key=api_key)
        return _gemini_client
    except Exception as exc:
        logger.warning("Gemini SDK unavailable: %s", exc)
        return None

async def shield_message_async(text: str) -> dict:
    """Analyze message using Shield 1 (Regex) then Shield 2 (AI)."""
    if not text:
        return {"action": "allow", "reason": None, "entity": None}

    # Instant rigid block
    for pattern in [INDIAN_MOBILE, AADHAAR, EMAIL, URL]:
        if pattern.search(text):
            return {"action": "block", "reason": "pii_or_external_link", "entity": None}

    if TOXICITY_RED.search(text) or SELF_HARM_FAST.search(text) or SUBSTANCE_FAST.search(text):
        return {"action": "block", "reason": "safety_policy_violation", "entity": None}

    # Primary Moderation Layer (Contextual)
    client = _get_gemini_client()
    if client:
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=f'Analyze for ZENK Impact policy: "{text}"',
                config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.0}
            )
            text_response = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text_response)
            return {
                "action": result.get("action", "allow"),
                "reason": result.get("reason"),
                "entity": result.get("entity"),
            }
        except Exception as exc:
            logger.warning("Moderation API error: %s", exc)

    # Fallback Logic (Service Unavailability)
    return _legacy_shield(text)

def shield_message(text: str) -> dict:
    """Sync wrapper for legacy callers."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return _legacy_shield(text)
        return loop.run_until_complete(shield_message_async(text))
    except Exception:
        return _legacy_shield(text)

def _legacy_shield(text: str) -> dict:
    """Refined safety-net fallback if Gemini is unavailable."""
    if TOXICITY_RED.search(text) or SELF_HARM_FAST.search(text) or SUBSTANCE_FAST.search(text):
        return {"action": "block", "reason": "safety_policy_violation", "entity": None}

    if INDIAN_MOBILE.search(text) or EMAIL.search(text) or URL.search(text):
        return {"action": "block", "reason": "pii_or_external_link", "entity": None}

    if GEOPOLITICAL_SAFETY.search(text) or VIOLENCE_CONTEXT_SAFETY.search(text):
        return {"action": "block", "reason": "off_topic_content", "entity": None}

    if OFF_PLATFORM_HINTS.search(text):
        return {"action": "block", "reason": "off_platform_intent", "entity": None}

    if SOCIAL_HANDLE.search(text):
        return {"action": "warn", "reason": "social_handle_detected", "entity": "SOCIAL_HANDLE"}

    return {"action": "allow", "reason": None, "entity": None}
