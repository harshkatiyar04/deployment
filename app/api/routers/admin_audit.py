from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from app.models.auth_log import AuthAuditLog
from app.core.admin_deps import require_admin_api_key
from app.chat.schemas import AuthLogResponse

router = APIRouter(
    prefix="/admin/chat",
    tags=["admin_audit"],
    dependencies=[Depends(require_admin_api_key)],
)


@router.get("/auth-logs", response_model=List[AuthLogResponse])
async def list_auth_logs(db: AsyncSession = Depends(get_db)):
    """
    Fetch the latest 100 authentication audit logs for administrators.
    """
    stmt = (
        select(AuthAuditLog)
        .order_by(AuthAuditLog.timestamp.desc())
        .limit(100)
    )
    res = await db.execute(stmt)
    return res.scalars().all()
