from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CalendarBlockCreate(BaseModel):
    venue_id: str
    start_at: datetime
    end_at: datetime
    reason: str = Field(default="", max_length=255)


class CalendarBlockOut(BaseModel):
    id: str
    venue_id: str
    start_at: datetime
    end_at: datetime
    reason: str

    class Config:
        from_attributes = True
