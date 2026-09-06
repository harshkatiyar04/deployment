"""Public landing Kia ask — platform-scoped RAG + fast TTS."""

import base64
import logging
from typing import List, Optional

from fastapi import APIRouter, Body, Request, status
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.services.landing_kia_kb import SUGGESTION_PROMPTS
from app.services.landing_kia_rag import answer_question
from app.services.landing_kia_tts import lookup_cached, synthesize

router = APIRouter(prefix="/landing/kia", tags=["landing-kia"])
logger = logging.getLogger(__name__)


class KiaAskIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    speak: bool = False
    first_turn: bool = False


class KiaAskOut(BaseModel):
    ok: bool = True
    refused: bool = False
    answer: str
    chunk_ids: List[str] = Field(default_factory=list)
    fast: bool = False
    audio_base64: Optional[str] = None
    audio_mime: str = "audio/mpeg"


class KiaSpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=1200)


class KiaSpeakOut(BaseModel):
    ok: bool = True
    audio_base64: Optional[str] = None
    audio_mime: str = "audio/mpeg"


class KiaMetaOut(BaseModel):
    ok: bool = True
    language: str = "en"
    suggestions: List[str]


@router.get("/meta", response_model=KiaMetaOut)
async def kia_meta():
    return KiaMetaOut(suggestions=list(SUGGESTION_PROMPTS))


@router.post("/ask", response_model=KiaAskOut, status_code=status.HTTP_200_OK)
@limiter.limit("40/hour")
async def kia_ask(
    request: Request,
    payload: KiaAskIn = Body(...),
):
    result = answer_question(payload.question, first_turn=bool(payload.first_turn))
    answer = result.get("answer") or ""
    audio_b64 = None
    audio_mime = "audio/mpeg"

    # Attach cached audio on the ask itself — zero extra round-trip when warm
    if answer:
        cached = lookup_cached(answer)
        if cached:
            audio, audio_mime = cached
            audio_b64 = base64.b64encode(audio).decode("ascii")
        elif payload.speak:
            try:
                spoken = await synthesize(answer)
                if spoken:
                    audio, audio_mime = spoken
                    audio_b64 = base64.b64encode(audio).decode("ascii")
            except Exception as exc:
                logger.warning("Kia TTS skipped: %s", exc)

    return KiaAskOut(
        ok=bool(result.get("ok", True)),
        refused=bool(result.get("refused")),
        answer=answer,
        chunk_ids=list(result.get("chunk_ids") or []),
        fast=bool(result.get("fast")),
        audio_base64=audio_b64,
        audio_mime=audio_mime,
    )


@router.post("/speak", response_model=KiaSpeakOut, status_code=status.HTTP_200_OK)
@limiter.limit("40/hour")
async def kia_speak(
    request: Request,
    payload: KiaSpeakIn = Body(...),
):
    audio_b64 = None
    audio_mime = "audio/mpeg"
    try:
        spoken = await synthesize(payload.text)
        if spoken:
            audio, audio_mime = spoken
            audio_b64 = base64.b64encode(audio).decode("ascii")
    except Exception as exc:
        logger.warning("Kia speak failed: %s", exc)
    return KiaSpeakOut(ok=True, audio_base64=audio_b64, audio_mime=audio_mime)
