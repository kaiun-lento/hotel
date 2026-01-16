from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Permission(Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
