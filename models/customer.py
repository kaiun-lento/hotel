from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    phone_normalized: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    phone_masked: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    email_normalized: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    email_masked: Mapped[str] = mapped_column(String(255), nullable=False, default="")
