from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin


class MenuCategory(Base, TimestampMixin):
    __tablename__ = "menu_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    items: Mapped[list["MenuItem"]] = relationship("MenuItem", back_populates="category", cascade="all, delete-orphan")


class MenuItem(Base, TimestampMixin):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("menu_categories.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")

    type: Mapped[str] = mapped_column(String(32), nullable=False, default="BENTO")  # BENTO/COURSE/BUFFET/DRINK/OPTION
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    category: Mapped[MenuCategory] = relationship("MenuCategory", back_populates="items")
    photos: Mapped[list["MenuItemPhoto"]] = relationship("MenuItemPhoto", back_populates="menu_item", cascade="all, delete-orphan")


class MenuItemPhoto(Base, TimestampMixin):
    __tablename__ = "menu_item_photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    menu_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("menu_items.id"), nullable=False, index=True)

    image_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    menu_item: Mapped[MenuItem] = relationship("MenuItem", back_populates="photos")
