from __future__ import annotations

import hashlib
import secrets
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.calendar_block import CalendarBlock
from app.models.booking_rule import BookingRule
from app.models.customer import Customer
from app.models.reservation import Reservation, ReservationMenuSelection
from app.models.reservation_token import ReservationAccessToken
from app.models.venue import Venue
from app.services.auth_service import (
    generate_public_id,
    hash_pii,
    mask_email,
    mask_phone,
    normalize_email,
    normalize_phone,
)
from app.services.mailer import send_email
from app.services.settings_service import get_or_create_settings


def _hash_token(raw: str) -> str:
    settings = get_settings()
    return hashlib.sha256((settings.secret_key + "|" + raw).encode("utf-8")).hexdigest()


def _ensure_same_local_date(start_at: datetime, end_at: datetime, tz: ZoneInfo) -> None:
    if start_at.astimezone(tz).date() != end_at.astimezone(tz).date():
        raise HTTPException(status_code=400, detail="Reservation must be within a single day")


def _ensure_within_business_hours(start_at: datetime, end_at: datetime, tz: ZoneInfo, start: time, end: time) -> None:
    ls = start_at.astimezone(tz)
    le = end_at.astimezone(tz)
    if not (start <= ls.time() <= end and start <= le.time() <= end):
        raise HTTPException(status_code=400, detail="Outside business hours")


def _apply_same_day_cutoff(start_at: datetime, now: datetime, tz: ZoneInfo, cutoff: time) -> None:
    if start_at.astimezone(tz).date() == now.astimezone(tz).date():
        if now.astimezone(tz).time() >= cutoff:
            raise HTTPException(status_code=400, detail="Same-day booking is closed")


def _apply_lead_time(start_at: datetime, now: datetime, lead_minutes: int) -> None:
    if start_at - now < timedelta(minutes=lead_minutes):
        raise HTTPException(status_code=400, detail="Too late to book")


def _has_calendar_block(db: Session, venue_id: str, start_at: datetime, end_at: datetime) -> bool:
    q = (
        select(CalendarBlock.id)
        .where(CalendarBlock.venue_id == venue_id)
        .where(CalendarBlock.start_at < end_at)
        .where(CalendarBlock.end_at > start_at)
        .limit(1)
    )
    return db.execute(q).first() is not None


def _has_overlapping_reservation(db: Session, venue_id: str, start_at: datetime, end_at: datetime, exclude_reservation_id: str | None = None) -> bool:
    q = (
        select(Reservation.id)
        .where(Reservation.venue_id == venue_id)
        .where(Reservation.status != "CANCELLED")
        .where(Reservation.start_at < end_at)
        .where(Reservation.end_at > start_at)
    )
    if exclude_reservation_id:
        q = q.where(Reservation.id != exclude_reservation_id)
    q = q.limit(1)
    return db.execute(q).first() is not None


def validate_reservation_time(
    db: Session,
    *,
    venue_id: str,
    start_at: datetime,
    end_at: datetime,
    now: datetime | None = None,
    exclude_reservation_id: str | None = None,
) -> None:
    settings = get_or_create_settings(db)
    app_settings = get_settings()
    tz = ZoneInfo(app_settings.timezone)

    if now is None:
        now = datetime.now(tz=ZoneInfo("UTC"))

    if start_at >= end_at:
        raise HTTPException(status_code=400, detail="Invalid time range")

    if start_at < now:
        raise HTTPException(status_code=400, detail="Start time is in the past")

    _ensure_same_local_date(start_at, end_at, tz)
    _ensure_within_business_hours(start_at, end_at, tz, settings.business_hours_start, settings.business_hours_end)
    _apply_same_day_cutoff(start_at, now, tz, settings.same_day_cutoff)
    _apply_lead_time(start_at, now, settings.lead_time_minutes)

    # Evaluate additional booking rules (active)
    rules_q = (
        select(BookingRule)
        .where(BookingRule.is_active == True)
        .where(
            or_(
                BookingRule.scope_type == "ALL",
                and_(BookingRule.scope_type == "VENUE", BookingRule.scope_id == venue_id),
            )
        )
    )
    rules = db.execute(rules_q).scalars().all()

    local_start = start_at.astimezone(tz)
    local_end = end_at.astimezone(tz)
    local_now = now.astimezone(tz)

    for rule in rules:
        rt = (rule.rule_type or "").upper()
        params = rule.params_json or {}

        if rt == "WEEKLY_CLOSED":
            weekdays = params.get("weekdays") if isinstance(params, dict) else None
            if weekdays is None and isinstance(params, dict):
                weekdays = params.get("weekday")
            if isinstance(weekdays, int):
                weekdays = [weekdays]
            if isinstance(weekdays, list) and local_start.weekday() in weekdays:
                raise HTTPException(status_code=400, detail="Closed day")

        elif rt == "CLOSED_DATE_RANGE":
            if not isinstance(params, dict):
                continue
            sd = params.get("start_date")
            ed = params.get("end_date")
            if sd and ed:
                try:
                    sd_d = date.fromisoformat(sd)
                    ed_d = date.fromisoformat(ed)
                except ValueError:
                    continue
                if sd_d <= local_start.date() <= ed_d:
                    raise HTTPException(status_code=400, detail="Closed date")

        elif rt == "TIME_WINDOW":
            if not isinstance(params, dict):
                continue
            st = params.get("start")
            en = params.get("end")
            if st and en:
                try:
                    st_t = time.fromisoformat(st)
                    en_t = time.fromisoformat(en)
                except ValueError:
                    continue
                if not (st_t <= local_start.time() <= en_t and st_t <= local_end.time() <= en_t):
                    raise HTTPException(status_code=400, detail="Outside allowed time")

        elif rt == "SAME_DAY_CUTOFF":
            if not isinstance(params, dict):
                continue
            ct = params.get("time")
            if ct:
                try:
                    ct_t = time.fromisoformat(ct)
                except ValueError:
                    continue
                if local_start.date() == local_now.date() and local_now.time() >= ct_t:
                    raise HTTPException(status_code=400, detail="Same-day booking is closed")

        elif rt == "LEAD_TIME":
            if not isinstance(params, dict):
                continue
            minutes = params.get("minutes")
            if minutes is None:
                hours = params.get("hours")
                if hours is not None:
                    try:
                        minutes = int(hours) * 60
                    except Exception:
                        minutes = None
            if minutes is not None:
                try:
                    minutes_i = int(minutes)
                except Exception:
                    continue
                if start_at - now < timedelta(minutes=minutes_i):
                    raise HTTPException(status_code=400, detail="Too late to book")

    if _has_calendar_block(db, venue_id, start_at, end_at):
        raise HTTPException(status_code=400, detail="Not available")

    if _has_overlapping_reservation(db, venue_id, start_at, end_at, exclude_reservation_id=exclude_reservation_id):
        raise HTTPException(status_code=409, detail="Time slot already booked")


def get_or_create_customer(db: Session, *, name: str, phone: str, email: str) -> Customer:
    phone_norm = normalize_phone(phone)
    email_norm = normalize_email(email)

    phone_h = hash_pii(phone_norm) if phone_norm else ""
    email_h = hash_pii(email_norm) if email_norm else ""

    customer = None
    if phone_h:
        customer = db.execute(select(Customer).where(Customer.phone_hash == phone_h)).scalar_one_or_none()
    if customer is None and email_h:
        customer = db.execute(select(Customer).where(Customer.email_hash == email_h)).scalar_one_or_none()

    if customer is None:
        customer = Customer(
            name=name,
            phone_normalized=phone_norm,
            phone_hash=phone_h,
            phone_masked=mask_phone(phone_norm),
            email_normalized=email_norm,
            email_hash=email_h,
            email_masked=mask_email(email_norm),
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    # update contact info if missing
    updated = False
    if name and customer.name != name:
        customer.name = name
        updated = True
    if phone_norm and customer.phone_normalized != phone_norm:
        customer.phone_normalized = phone_norm
        customer.phone_hash = phone_h
        customer.phone_masked = mask_phone(phone_norm)
        updated = True
    if email_norm and customer.email_normalized != email_norm:
        customer.email_normalized = email_norm
        customer.email_hash = email_h
        customer.email_masked = mask_email(email_norm)
        updated = True

    if updated:
        db.commit()
    return customer


def create_reservation_public(
    db: Session,
    *,
    venue_id: str,
    start_at: datetime,
    end_at: datetime,
    people_count: int,
    booking_type: str,
    banquet_name: str,
    desired_time_text: str,
    customer_name: str,
    phone: str,
    email: str,
    menu_selections: list[dict],
    consent_version: str,
) -> Reservation:
    # Validate venue exists
    venue = db.get(Venue, venue_id)
    if not venue or not venue.active:
        raise HTTPException(status_code=404, detail="Venue not found")

    validate_reservation_time(db, venue_id=venue_id, start_at=start_at, end_at=end_at)

    customer = get_or_create_customer(db, name=customer_name, phone=phone, email=email)

    public_id = generate_public_id()
    # Avoid collisions
    for _ in range(5):
        exists = db.execute(select(Reservation.id).where(Reservation.public_id == public_id)).first()
        if not exists:
            break
        public_id = generate_public_id()

    reservation = Reservation(
        public_id=public_id,
        venue_id=venue_id,
        customer_id=customer.id,
        start_at=start_at,
        end_at=end_at,
        people_count=people_count,
        booking_type=booking_type,
        banquet_name=banquet_name or "",
        status="PENDING",
        desired_time_text=desired_time_text or "",
        consent_version=consent_version or "",
        consent_at=datetime.now(tz=ZoneInfo("UTC")),
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    # Menu selections
    for sel in menu_selections or []:
        db.add(
            ReservationMenuSelection(
                reservation_id=reservation.id,
                menu_item_id=sel["menu_item_id"],
                quantity=int(sel.get("quantity", 1)),
                notes=str(sel.get("notes", ""))[:255],
            )
        )
    db.commit()

    # Create access token
    token_raw = secrets.token_urlsafe(24)
    token_hash = _hash_token(token_raw)

    settings_row = get_or_create_settings(db)

    token = ReservationAccessToken(
        reservation_id=reservation.id,
        token_hash=token_hash,
        purpose="VIEW",
        expires_at=datetime.now(tz=ZoneInfo("UTC")) + timedelta(days=settings_row.reservation_token_ttl_days),
        max_views=settings_row.reservation_token_max_views,
        view_count=0,
        last_accessed_at=None,
    )
    db.add(token)
    db.commit()

    # Send confirmation email
    app_settings = get_settings()
    link = f"{app_settings.public_base_url.rstrip('/')}/r/{token_raw}"
    subject = "仮予約を受け付けました"
    body = (
        f"仮予約を受け付けました。\n\n"
        f"予約ID: {reservation.public_id}\n"
        f"会場: {venue.name}\n"
        f"日時: {reservation.start_at.astimezone(ZoneInfo(app_settings.timezone)).strftime('%Y-%m-%d %H:%M')} - "
        f"{reservation.end_at.astimezone(ZoneInfo(app_settings.timezone)).strftime('%H:%M')}\n"
        f"人数: {reservation.people_count}\n\n"
        f"予約内容の確認・キャンセル: {link}\n\n"
        f"※このリンクは一定期間・一定回数のみ有効です。\n"
    )
    send_email(email, subject, body)

    return reservation


def lookup_reservation_by_public_id_and_phone(db: Session, *, public_id: str, phone: str) -> Reservation:
    reservation = db.execute(select(Reservation).where(Reservation.public_id == public_id)).scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Not found")

    customer = db.get(Customer, reservation.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Not found")

    phone_norm = normalize_phone(phone)
    if not phone_norm:
        raise HTTPException(status_code=400, detail="Invalid phone")

    if hash_pii(phone_norm) != customer.phone_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return reservation


def get_reservation_by_token(db: Session, *, token_raw: str) -> Reservation:
    token_hash = _hash_token(token_raw)
    token = db.execute(select(ReservationAccessToken).where(ReservationAccessToken.token_hash == token_hash)).scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Invalid token")

    now = datetime.now(tz=ZoneInfo("UTC"))
    if now > token.expires_at:
        raise HTTPException(status_code=410, detail="Token expired")

    if token.view_count >= token.max_views:
        raise HTTPException(status_code=410, detail="Token view limit reached")

    token.view_count += 1
    token.last_accessed_at = now
    db.commit()

    reservation = db.get(Reservation, token.reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Not found")
    return reservation


def cancel_reservation(db: Session, *, reservation: Reservation, reason: str = "") -> None:
    if reservation.status == "CANCELLED":
        return
    reservation.status = "CANCELLED"
    reservation.cancel_reason = reason[:255]
    reservation.cancelled_at = datetime.now(tz=ZoneInfo("UTC"))
    db.commit()
