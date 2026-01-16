from __future__ import annotations

from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = ""


class RoleCreate(RoleBase):
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    permission_codes: list[str] | None = None


class RoleOut(RoleBase):
    id: str
    permission_codes: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
