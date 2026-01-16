from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    summary: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    diff_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    user_agent: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
