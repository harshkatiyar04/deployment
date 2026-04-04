"""Pydantic schemas for the chat system.

SECURITY: MessageOut and all broadcast payloads deliberately exclude user_id and
real name. Only persona_id, persona_nickname, and avatar_key are exposed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator
import json

# ---------------------------------------------------------------------------
# WebSocket envelope
# ---------------------------------------------------------------------------


class WSEnvelope(BaseModel):
    type: str
    payload: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Inbound message schemas (client -> server)
# ---------------------------------------------------------------------------


class MessageSend(BaseModel):
    channel_id: UUID
    content_text: Optional[str] = None
    media_url: Optional[str] = None


class SOSReportIn(BaseModel):
    message_id: UUID


# ---------------------------------------------------------------------------
# Outbound schemas (server -> client / REST responses)
# ---------------------------------------------------------------------------


class PersonaOut(BaseModel):
    id: str
    nickname: str
    avatar_key: str


class MessageOut(BaseModel):
    id: str
    channel_id: str
    gamified_persona_id: str
    persona_nickname: str
    avatar_key: str
    content_text: Optional[str] = None
    media_url: Optional[str] = None
    shield_action: str
    created_at: datetime
    deleted_at: Optional[datetime] = None


class CircleMemberOut(BaseModel):
    persona_id: str
    nickname: str
    avatar_key: str
    role: str
    joined_at: datetime


class ChannelOut(BaseModel):
    id: str
    circle_id: str
    name: str
    channel_type: str
    created_at: datetime


class ChannelCreate(BaseModel):
    name: str
    channel_type: str = "persistent"
    circle_id: str


class SOSReportOut(BaseModel):
    id: str
    message_id: str
    reporter_persona_id: str
    hidden_at: Optional[datetime] = None
    admin_notified_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    message_content: Optional[str] = None
    media_url: Optional[str] = None
    sender_user_id: Optional[str] = None
    sender_nickname: Optional[str] = None
    reporter_nickname: Optional[str] = None
    circle_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Admin & Moderation Schemas
# ---------------------------------------------------------------------------


class BanCreate(BaseModel):
    circle_id: UUID
    user_identifier: str  # Can be UUID or Email
    reason: str
    reported_message_content: Optional[str] = None


class BanResponse(BaseModel):
    id: UUID
    circle_id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    banned_by_admin_id: Optional[UUID] = None
    reason: str
    reported_message_content: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BanListResponse(BaseModel):
    bans: List[BanResponse]


class ActivityResponse(BaseModel):
    id: UUID
    admin_id: UUID
    admin_email: Optional[str] = None
    action: str
    target_table: str
    target_id: UUID
    changes_json: Optional[dict] = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def parse_json(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cj = data.get("changes_json")
            if isinstance(cj, str):
                try:
                    data["changes_json"] = json.loads(cj)
                except Exception:
                    data["changes_json"] = {}
        return data

    model_config = ConfigDict(from_attributes=True)


class WarnedMessageOut(BaseModel):
    id: str
    channel_id: str
    gamified_persona_id: str
    persona_nickname: str
    content_text: Optional[str] = None
    media_url: Optional[str] = None
    shield_reason: Optional[str] = None
    created_at: datetime
    sender_user_id: Optional[str] = None
    circle_id: str
