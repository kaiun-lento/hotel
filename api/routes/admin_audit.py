from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_permissions
from app.models.audit_log import AuditLog
from app.models.auth_event import AuthEvent
from app.models.permission import Permission
from app.schemas.audit import AuditLogOut

router = APIRouter()


@router.get("/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    actor_user_id: str | None = None,
    action_type: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_permissions(["AUDIT_VIEW"])),
):
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if from_:
        q = q.where(AuditLog.created_at >= from_)
    if to:
        q = q.where(AuditLog.created_at <= to)
    if actor_user_id:
        q = q.where(AuditLog.actor_user_id == actor_user_id)
    if action_type:
        q = q.where(AuditLog.action_type == action_type)
    if target_type:
        q = q.where(AuditLog.target_type == target_type)
    if target_id:
        q = q.where(AuditLog.target_id == target_id)

    logs = db.execute(q.limit(500)).scalars().all()
    return logs


@router.get("/auth-events")
def list_auth_events(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    user_id: str | None = None,
    event_type: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_permissions(["AUDIT_VIEW"])),
):
    q = select(AuthEvent).order_by(AuthEvent.created_at.desc())
    if from_:
        q = q.where(AuthEvent.created_at >= from_)
    if to:
        q = q.where(AuthEvent.created_at <= to)
    if user_id:
        q = q.where(AuthEvent.user_id == user_id)
    if event_type:
        q = q.where(AuthEvent.event_type == event_type)

    events = db.execute(q.limit(500)).scalars().all()
    return [
        {
            "id": e.id,
            "user_id": e.user_id,
            "event_type": e.event_type,
            "ip_address": e.ip_address,
            "user_agent": e.user_agent,
            "failure_reason": e.failure_reason,
            "created_at": e.created_at,
        }
        for e in events
    ]


@router.get("/permissions")
def list_permissions(db: Session = Depends(get_db), user=Depends(require_permissions(["AUDIT_VIEW"]))):
    perms = db.execute(select(Permission).order_by(Permission.category, Permission.code)).scalars().all()
    return [{"code": p.code, "category": p.category, "description": p.description} for p in perms]
