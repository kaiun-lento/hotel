from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin


class Venue(Base, TimestampMixin):
    __tablename__ = "venues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Optional: used later for monthly print column grouping
    print_group: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    print_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
