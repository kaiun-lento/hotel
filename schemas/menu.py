from __future__ import annotations

from pydantic import BaseModel, Field


class MenuCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sort_order: int = 0
    active: bool = True


class MenuCategoryOut(BaseModel):
    id: str
    name: str
    sort_order: int
    active: bool

    class Config:
        from_attributes = True


class MenuItemCreate(BaseModel):
    category_id: str
    name: str = Field(min_length=1, max_length=200)
    description: str | None = ""
    price: int = Field(default=0, ge=0)
    active: bool = True


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: int | None = Field(default=None, ge=0)
    active: bool | None = None


class MenuPhotoCreate(BaseModel):
    url: str = Field(min_length=3, max_length=1000)
    alt_text: str | None = ""


class MenuPhotoOut(BaseModel):
    id: str
    menu_item_id: str
    url: str
    alt_text: str

    class Config:
        from_attributes = True


class MenuItemOut(BaseModel):
    id: str
    category_id: str
    name: str
    description: str
    price: int
    active: bool
    photos: list[MenuPhotoOut] = []

    class Config:
        from_attributes = True
