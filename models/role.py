from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    permissions: Mapped[list["RolePermission"]] = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), primary_key=True)
    permission_code: Mapped[str] = mapped_column(String(64), ForeignKey("permissions.code"), primary_key=True)

    role: Mapped[Role] = relationship("Role", back_populates="permissions")
