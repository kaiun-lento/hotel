from __future__ import annotations

from pydantic import BaseModel, Field


class VenueCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sort_order: int = 0
    active: bool = True


class VenueUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sort_order: int | None = None
    active: bool | None = None


class VenueOut(BaseModel):
    id: str
    name: str
    sort_order: int
    active: bool
    print_group: str
    print_order: int

    class Config:
        from_attributes = True
