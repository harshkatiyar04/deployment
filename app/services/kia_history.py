"""Helpers to build LLM chat history for Kia across surfaces."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.chat.models import ChatMessage

# Cap of prior turns sent to the model (user+assistant pairs ≈ half of this).
LLM_HISTORY_MESSAGE_CAP = 20


def role_text_rows_to_history(
    rows: Sequence[Any],
    *,
    exclude_trailing_user_text: Optional[str] = None,
    assistant_roles: frozenset[str] = frozenset({"kia", "assistant"}),
    user_roles: frozenset[str] = frozenset({"user"}),
    limit: int = LLM_HISTORY_MESSAGE_CAP,
) -> list[dict[str, str]]:
    """
    Convert persisted role/text rows into OpenAI-style history.

    Rows must expose `.role` and `.text` (or `.content_text`).
    The current user turn should be passed separately as user_message — exclude it here.
    """
    items: list[tuple[str, str]] = []
    for row in rows:
        role_raw = (getattr(row, "role", None) or "").strip().lower()
        text = (
            getattr(row, "text", None)
            or getattr(row, "content_text", None)
            or ""
        )
        text = str(text).strip()
        if not text:
            continue
        if role_raw in assistant_roles:
            items.append(("assistant", text))
        elif role_raw in user_roles:
            items.append(("user", text))

    if exclude_trailing_user_text and items:
        trail = (exclude_trailing_user_text or "").strip()
        if trail and items[-1][0] == "user" and items[-1][1] == trail:
            items = items[:-1]

    if limit > 0 and len(items) > limit:
        items = items[-limit:]

    return [{"role": role, "content": content} for role, content in items]


async def load_circle_channel_history(
    db: AsyncSession,
    channel_id: str,
    *,
    kia_persona_id: str,
    exclude_trailing_user_text: Optional[str] = None,
    limit: int = LLM_HISTORY_MESSAGE_CAP,
) -> list[dict[str, str]]:
    """Load recent circle chat messages as LLM history (Kia → assistant)."""
    # Fetch newest first, then reverse for chronological order.
    fetch_n = max(limit + 2, limit)
    res = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.channel_id == channel_id,
            ChatMessage.deleted_at.is_(None),
            ChatMessage.hidden_at.is_(None),
            ChatMessage.content_text.isnot(None),
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(fetch_n)
        .options(selectinload(ChatMessage.persona))
    )
    rows = list(reversed(res.scalars().all()))

    # Lightweight stand-ins with .role / .text for the shared mapper.
    class _Row:
        __slots__ = ("role", "text")

        def __init__(self, role: str, text: str):
            self.role = role
            self.text = text

    mapped: list[_Row] = []
    for msg in rows:
        text = (msg.content_text or "").strip()
        if not text:
            continue
        persona = msg.persona
        nick = (persona.nickname if persona else "") or ""
        if str(msg.gamified_persona_id) == str(kia_persona_id) or nick.lower() == "kia":
            mapped.append(_Row("kia", text))
        else:
            mapped.append(_Row("user", text))

    return role_text_rows_to_history(
        mapped,
        exclude_trailing_user_text=exclude_trailing_user_text,
        limit=limit,
    )
