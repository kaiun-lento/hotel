from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role_ids: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    is_active: bool
    is_root_admin: bool
    last_login_at: datetime | None
    role_ids: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
