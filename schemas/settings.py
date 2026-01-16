from __future__ import annotations

from datetime import time

from pydantic import BaseModel, Field


class SettingsOut(BaseModel):
    public_day_start: time
    public_day_end: time
    public_night_start: time
    public_night_end: time

    reservation_token_ttl_days: int
    reservation_token_max_views: int

    auto_expire_enabled: bool
    auto_expire_hours: int

    same_day_cutoff: time
    lead_time_minutes: int

    business_hours_start: time
    business_hours_end: time

    cancel_policy_url: str
    cancel_policy_version: str

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    public_day_start: time | None = None
    public_day_end: time | None = None
    public_night_start: time | None = None
    public_night_end: time | None = None

    reservation_token_ttl_days: int | None = Field(default=None, ge=1, le=365)
    reservation_token_max_views: int | None = Field(default=None, ge=1, le=1000)

    auto_expire_enabled: bool | None = None
    auto_expire_hours: int | None = Field(default=None, ge=1, le=720)

    same_day_cutoff: time | None = None
    lead_time_minutes: int | None = Field(default=None, ge=0, le=10080)

    business_hours_start: time | None = None
    business_hours_end: time | None = None

    cancel_policy_url: str | None = None
    cancel_policy_version: str | None = None
