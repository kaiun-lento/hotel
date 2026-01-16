from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin


class BookingRule(Base, TimestampMixin):
    __tablename__ = "booking_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # e.g. WEEKLY_CLOSED, CLOSED_DATE_RANGE, TIME_WINDOW, SAME_DAY_CUTOFF, LEAD_TIME
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # scope_type: ALL | VENUE | GROUP
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False, default="ALL")
    scope_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    params_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
