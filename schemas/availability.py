from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class AvailabilityBlock(BaseModel):
    venue_id: str
    venue_name: str
    date: date
    block: str  # DAY/NIGHT
    status: str  # O/X


class AvailabilityResponse(BaseModel):
    blocks: list[AvailabilityBlock]
