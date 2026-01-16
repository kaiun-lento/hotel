from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class MenuSelectionIn(BaseModel):
    menu_item_id: str
    quantity: int = Field(default=1, ge=1, le=999)
    notes: str = Field(default="", max_length=255)


class PublicReservationCreate(BaseModel):
    venue_id: str
    start_at: datetime
    end_at: datetime
    people_count: int = Field(ge=1, le=9999)

    booking_type: str = Field(default="BANQUET")  # BANQUET/MEETING/OTHER
    banquet_name: str = Field(default="", max_length=255)

    customer_name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=6, max_length=32)
    email: EmailStr

    desired_time_text: str = Field(default="", max_length=64)

    menu_selections: list[MenuSelectionIn] = Field(default_factory=list)

    consent_accepted: bool = True
    consent_version: str = Field(default="", max_length=64)

    # Optional CAPTCHA token
    captcha_token: str | None = None


class PublicReservationCreated(BaseModel):
    public_id: str
    message: str


class PublicReservationLookupRequest(BaseModel):
    public_id: str
    phone: str


class PublicReservationCancelRequest(BaseModel):
    phone: str
    reason: str = Field(default="", max_length=255)


class ReservationOut(BaseModel):
    public_id: str
    venue_id: str
    start_at: datetime
    end_at: datetime
    people_count: int
    booking_type: str
    banquet_name: str
    status: str
    desired_time_text: str
    menu_selections: list[MenuSelectionIn] = Field(default_factory=list)


class AdminReservationUpdate(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    people_count: int | None = Field(default=None, ge=1, le=9999)
    booking_type: str | None = None
    banquet_name: str | None = Field(default=None, max_length=255)
    desired_time_text: str | None = Field(default=None, max_length=64)


class AdminReservationOut(ReservationOut):
    id: str
    customer_id: str

    class Config:
        from_attributes = True
