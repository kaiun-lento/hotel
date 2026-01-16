from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin


class CalendarBlock(Base, TimestampMixin):
    __tablename__ = "calendar_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    venue_id: Mapped[str] = mapped_column(String(36), ForeignKey("venues.id"), nullable=False, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
