from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin


class Reservation(Base, TimestampMixin):
    __tablename__ = "reservations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    public_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)

    venue_id: Mapped[str] = mapped_column(String(36), ForeignKey("venues.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False, index=True)

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    people_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    booking_type: Mapped[str] = mapped_column(String(32), nullable=False, default="BANQUET")  # BANQUET/MEETING/OTHER
    banquet_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")  # PENDING/CANCELLED

    desired_time_text: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    menu_selections: Mapped[list["ReservationMenuSelection"]] = relationship(
        "ReservationMenuSelection", back_populates="reservation", cascade="all, delete-orphan"
    )


class ReservationMenuSelection(Base):
    __tablename__ = "reservation_menu_selections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reservation_id: Mapped[str] = mapped_column(String(36), ForeignKey("reservations.id"), nullable=False, index=True)
    menu_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("menu_items.id"), nullable=False, index=True)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    reservation: Mapped[Reservation] = relationship("Reservation", back_populates="menu_selections")
