from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.calendar_block import CalendarBlock
from app.models.reservation import Reservation
from app.models.venue import Venue
from app.services.reservation_service import validate_reservation_time
from app.services.settings_service import get_or_create_settings


def _daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur = cur + timedelta(days=1)


def compute_public_availability(db: Session, *, from_date: date, to_date: date) -> list[dict]:
    app_settings = get_settings()
    tz = ZoneInfo(app_settings.timezone)
    settings_row = get_or_create_settings(db)

    venues = db.execute(select(Venue).where(Venue.active == True).order_by(Venue.sort_order, Venue.name)).scalars().all()

    blocks: list[dict] = []

    # Preload reservations and blocks in range to reduce queries
    range_start_utc = datetime.combine(from_date, datetime.min.time()).replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
    range_end_utc = datetime.combine(to_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))

    reservations = db.execute(
        select(Reservation).where(
            Reservation.status != "CANCELLED",
            Reservation.start_at < range_end_utc,
            Reservation.end_at > range_start_utc,
        )
    ).scalars().all()

    blocks_db = db.execute(
        select(CalendarBlock).where(
            CalendarBlock.start_at < range_end_utc,
            CalendarBlock.end_at > range_start_utc,
        )
    ).scalars().all()

    def overlaps(items, venue_id: str, start_at: datetime, end_at: datetime) -> bool:
        for it in items:
            if getattr(it, "venue_id") != venue_id:
                continue
            if it.start_at < end_at and it.end_at > start_at:
                return True
        return False

    for d in _daterange(from_date, to_date):
        # Build two blocks in local time
        day_start_local = datetime.combine(d, settings_row.public_day_start).replace(tzinfo=tz)
        day_end_local = datetime.combine(d, settings_row.public_day_end).replace(tzinfo=tz)
        night_start_local = datetime.combine(d, settings_row.public_night_start).replace(tzinfo=tz)
        night_end_local = datetime.combine(d, settings_row.public_night_end).replace(tzinfo=tz)

        day_start = day_start_local.astimezone(ZoneInfo("UTC"))
        day_end = day_end_local.astimezone(ZoneInfo("UTC"))
        night_start = night_start_local.astimezone(ZoneInfo("UTC"))
        night_end = night_end_local.astimezone(ZoneInfo("UTC"))

        for venue in venues:
            # DAY
            status = "O"
            if overlaps(reservations, venue.id, day_start, day_end) or overlaps(blocks_db, venue.id, day_start, day_end):
                status = "X"
            else:
                # Also validate against rules/settings (e.g. closed day) using validate_reservation_time
                try:
                    validate_reservation_time(db, venue_id=venue.id, start_at=day_start, end_at=day_end)
                except Exception:
                    status = "X"
            blocks.append({"venue_id": venue.id, "venue_name": venue.name, "date": d, "block": "DAY", "status": status})

            # NIGHT
            status = "O"
            if overlaps(reservations, venue.id, night_start, night_end) or overlaps(blocks_db, venue.id, night_start, night_end):
                status = "X"
            else:
                try:
                    validate_reservation_time(db, venue_id=venue.id, start_at=night_start, end_at=night_end)
                except Exception:
                    status = "X"
            blocks.append({"venue_id": venue.id, "venue_name": venue.name, "date": d, "block": "NIGHT", "status": status})

    return blocks
