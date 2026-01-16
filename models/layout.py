from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin


class VenueLayoutTemplate(Base, TimestampMixin):
    __tablename__ = "venue_layout_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    venue_id: Mapped[str] = mapped_column(String(36), ForeignKey("venues.id"), nullable=False, unique=True)
    background_image_url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    canvas_width: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    canvas_height: Mapped[int] = mapped_column(Integer, nullable=False, default=800)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class LayoutAsset(Base, TimestampMixin):
    __tablename__ = "layout_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # If set, asset is limited to that venue; if empty, asset can be used across venues
    venue_id: Mapped[str] = mapped_column(String(36), ForeignKey("venues.id"), nullable=True)

    asset_type: Mapped[str] = mapped_column(String(32), nullable=False, default="TABLE")  # TABLE/CHAIR/OTHER
    shape: Mapped[str] = mapped_column(String(32), nullable=False, default="RECT")  # RECT/ROUND/etc
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    image_url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")

    default_width: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    default_height: Mapped[int] = mapped_column(Integer, nullable=False, default=80)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ReservationLayout(Base, TimestampMixin):
    __tablename__ = "reservation_layouts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reservation_id: Mapped[str] = mapped_column(String(36), ForeignKey("reservations.id"), nullable=False, unique=True)

    # Stores placed items, labels, seat assignment, etc.
    layout_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
