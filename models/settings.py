from __future__ import annotations

from datetime import time

from sqlalchemy import Boolean, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Public availability blocks (local time)
    public_day_start: Mapped[time] = mapped_column(Time, nullable=False, default=time(11, 0))
    public_day_end: Mapped[time] = mapped_column(Time, nullable=False, default=time(15, 0))
    public_night_start: Mapped[time] = mapped_column(Time, nullable=False, default=time(17, 0))
    public_night_end: Mapped[time] = mapped_column(Time, nullable=False, default=time(22, 0))

    # Reservation token link
    reservation_token_ttl_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    reservation_token_max_views: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    # Auto expire (optional)
    auto_expire_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_expire_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)

    # Booking time constraints
    same_day_cutoff: Mapped[time] = mapped_column(Time, nullable=False, default=time(20, 0))
    lead_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=180)

    # Business hours (local)
    business_hours_start: Mapped[time] = mapped_column(Time, nullable=False, default=time(10, 0))
    business_hours_end: Mapped[time] = mapped_column(Time, nullable=False, default=time(22, 0))

    # Consent URL/version (for audit)
    cancel_policy_url: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    cancel_policy_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
