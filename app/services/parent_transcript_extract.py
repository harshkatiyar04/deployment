"""AI extraction of term grades from parent-uploaded marksheets and transcripts."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from app.services.kia import _call_llm
from app.services.school_pdf_extract import (
    extract_text_from_pdf,
    merge_pdf_extraction,
    parse_marks_report_heuristics,
)

logger = logging.getLogger(__name__)

PARENT_EXTRACT_SYSTEM = """You extract term grades from Indian school marksheets and transcripts.
Return ONLY valid JSON.

Rules:
- maths_grade, science_grade, english_grade are display strings: letter grades (A, B+, C) or percentages (85%, 92).
- Map Mathematics/Math → maths_grade; Physics/Chemistry/Biology/Science → science_grade (average if several); English → english_grade.
- Use null when a subject is not clearly stated — never invent grades.
- quarter: Q1, Q2, Q3, or Q4 if mentioned (term 1→Q1, term 2→Q2, etc.); else null.
- confidence: high when marks are explicit, medium when inferred, low when uncertain."""

PARENT_GRADE_SCHEMA = """
{
  "quarter": "Q1|Q2|Q3|Q4 or null",
  "maths_grade": "string or null",
  "science_grade": "string or null",
  "english_grade": "string or null",
  "confidence": "high|medium|low",
  "notes": "brief extraction caveats"
}
"""


def _get_gemini_client():
    try:
        from app.core.settings import settings

        if not settings.gemini_api_key:
            return None
        from google import genai

        return genai.Client(api_key=settings.gemini_api_key)
    except Exception as exc:
        logger.warning("Gemini unavailable for parent extract: %s", exc)
        return None


def _score_to_grade_display(score: Any) -> Optional[str]:
    if score is None or score == "":
        return None
    if isinstance(score, str):
        s = score.strip()
        return s or None
    try:
        val = float(score)
    except (TypeError, ValueError):
        return str(score).strip() or None
    if 0 <= val <= 100:
        if val == int(val):
            return f"{int(val)}%"
        return f"{round(val, 1)}%"
    return str(score)


def _grades_from_subject_scores(subject_scores: dict[str, Any]) -> dict[str, Optional[str]]:
    src = subject_scores if isinstance(subject_scores, dict) else {}
    return {
        "maths_grade": _score_to_grade_display(src.get("maths")),
        "science_grade": _score_to_grade_display(src.get("science")),
        "english_grade": _score_to_grade_display(src.get("english")),
    }


def _has_any_grade(grades: dict[str, Optional[str]]) -> bool:
    return any((grades.get(k) or "").strip() for k in ("maths_grade", "science_grade", "english_grade"))


def _normalize_quarter(raw: Any) -> Optional[str]:
    if not raw:
        return None
    q = str(raw).strip().upper()
    if q in {"Q1", "Q2", "Q3", "Q4"}:
        return q
    return None


def _merge_grade_results(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    out = {**secondary}
    for key in ("quarter", "maths_grade", "science_grade", "english_grade", "confidence", "notes"):
        pv = primary.get(key)
        if pv not in (None, ""):
            out[key] = pv
    return out


async def llm_extract_parent_grades(document_text: str) -> dict[str, Any]:
    raw = await _call_llm(
        system_prompt=PARENT_EXTRACT_SYSTEM,
        user_message=f"DOCUMENT TEXT:\n{document_text[:12000]}\n\nReturn JSON only:\n{PARENT_GRADE_SCHEMA}",
        max_tokens=512,
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    if not raw:
        raise ValueError("AI extraction is unavailable. Enter grades manually or try again later.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Could not read grades from this document. Enter them manually.") from exc


async def gemini_extract_parent_grades_from_image(
    file_bytes: bytes,
    mime_type: str,
) -> dict[str, Any]:
    client = _get_gemini_client()
    if not client:
        raise ValueError(
            "Image marksheets need AI vision, which is not configured. "
            "Use a text-based PDF or enter grades manually."
        )

    prompt = (
        f"Read this student marksheet/transcript image and return JSON only:\n{PARENT_GRADE_SCHEMA}\n"
        f"{PARENT_EXTRACT_SYSTEM}"
    )
    try:
        from google.genai import types

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                        types.Part.from_text(text=prompt),
                    ],
                )
            ],
            config={"temperature": 0.1},
        )
        text = (response.text or "").replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as exc:
        logger.exception("Gemini parent grade extract failed: %s", exc)
        raise ValueError("Could not read grades from this image. Try a PDF or enter grades manually.") from exc


async def extract_parent_grades_from_bytes(
    file_bytes: bytes,
    *,
    content_type: str,
    filename: str = "",
) -> dict[str, Any]:
    mime = (content_type or "").lower()
    name = (filename or "").lower()

    if mime == "application/pdf" or name.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
        heuristic = parse_marks_report_heuristics(text) or {}
        llm_data = await llm_extract_parent_grades(text)
        if heuristic:
            merged = merge_pdf_extraction(heuristic, llm_data)
            grades = _grades_from_subject_scores(merged.get("subject_scores") or {})
            result = {
                "quarter": _normalize_quarter(merged.get("quarter") or llm_data.get("quarter")),
                **grades,
                "confidence": merged.get("confidence") or llm_data.get("confidence") or "medium",
                "notes": merged.get("notes") or llm_data.get("notes"),
            }
        else:
            result = {
                "quarter": _normalize_quarter(llm_data.get("quarter")),
                "maths_grade": (llm_data.get("maths_grade") or "").strip() or None,
                "science_grade": (llm_data.get("science_grade") or "").strip() or None,
                "english_grade": (llm_data.get("english_grade") or "").strip() or None,
                "confidence": llm_data.get("confidence") or "medium",
                "notes": llm_data.get("notes"),
            }
            if not _has_any_grade(result):
                h_grades = _grades_from_subject_scores((llm_data.get("subject_scores") or {}))
                result = _merge_grade_results(h_grades, result)

        if not _has_any_grade(result):
            raise ValueError(
                "No Maths, Science, or English grades found in this PDF. "
                "Check the file or enter grades manually."
            )
        return {
            "filled": True,
            "quarter": result.get("quarter"),
            "maths_grade": result.get("maths_grade"),
            "science_grade": result.get("science_grade"),
            "english_grade": result.get("english_grade"),
            "confidence": result.get("confidence") or "medium",
            "notes": result.get("notes"),
            "message": "Grades extracted — please review before submitting.",
        }

    if mime.startswith("image/"):
        llm_data = await gemini_extract_parent_grades_from_image(file_bytes, mime)
        result = {
            "quarter": _normalize_quarter(llm_data.get("quarter")),
            "maths_grade": (llm_data.get("maths_grade") or "").strip() or None,
            "science_grade": (llm_data.get("science_grade") or "").strip() or None,
            "english_grade": (llm_data.get("english_grade") or "").strip() or None,
            "confidence": llm_data.get("confidence") or "medium",
            "notes": llm_data.get("notes"),
        }
        if not _has_any_grade(result):
            raise ValueError(
                "No Maths, Science, or English grades found in this image. "
                "Enter grades manually or try a clearer photo/PDF."
            )
        return {
            "filled": True,
            **result,
            "message": "Grades extracted from image — please review before submitting.",
        }

    raise ValueError("Use PDF, JPG, PNG, or WebP for automatic grade extraction.")
