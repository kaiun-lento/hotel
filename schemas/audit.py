from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    created_at: datetime
    actor_user_id: str | None
    action_type: str
    target_type: str
    target_id: str
    summary: str
    diff_json: dict | None
    ip_address: str
    user_agent: str

    class Config:
        from_attributes = True
