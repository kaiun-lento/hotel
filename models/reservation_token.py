from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin


class ReservationAccessToken(Base, TimestampMixin):
    __tablename__ = "reservation_access_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    reservation_id: Mapped[str] = mapped_column(String(36), ForeignKey("reservations.id"), nullable=False, index=True)

    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    purpose: Mapped[str] = mapped_column(String(32), nullable=False, default="VIEW")

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    max_views: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
