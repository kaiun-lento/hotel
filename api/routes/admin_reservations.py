from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_db, require_permissions
from app.models.customer import Customer
from app.models.reservation import Reservation
from app.models.venue import Venue
from app.schemas.reservation import AdminReservationOut, AdminReservationUpdate
from app.services.audit_service import write_audit_log
from app.services.reservation_service import validate_reservation_time, cancel_reservation

router = APIRouter()


@router.get("", response_model=list[AdminReservationOut])
def list_reservations(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    venue_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_permissions(["RESERVATION_VIEW"])),
):
    q = select(Reservation)
    if from_date:
        # interpret as local day start
        app_settings = get_settings()
        tz = ZoneInfo(app_settings.timezone)
        start = datetime.combine(from_date, datetime.min.time()).replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
        q = q.where(Reservation.start_at >= start)
    if to_date:
        app_settings = get_settings()
        tz = ZoneInfo(app_settings.timezone)
        end = datetime.combine(to_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
        q = q.where(Reservation.start_at < end)
    if venue_id:
        q = q.where(Reservation.venue_id == venue_id)
    if status:
        q = q.where(Reservation.status == status)

    q = q.order_by(Reservation.start_at.asc())
    rows = db.execute(q.limit(1000)).scalars().all()
    return rows


@router.get("/{reservation_id}", response_model=AdminReservationOut)
def get_reservation(reservation_id: str, db: Session = Depends(get_db), user=Depends(require_permissions(["RESERVATION_VIEW"]))):
    r = db.get(Reservation, reservation_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    return r


@router.patch("/{reservation_id}", response_model=AdminReservationOut)
def update_reservation(reservation_id: str, payload: AdminReservationUpdate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["RESERVATION_EDIT"]))):
    r = db.get(Reservation, reservation_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")

    new_start = payload.start_at or r.start_at
    new_end = payload.end_at or r.end_at

    validate_reservation_time(db, venue_id=r.venue_id, start_at=new_start, end_at=new_end, exclude_reservation_id=r.id)

    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)

    write_audit_log(
        db,
        actor_user_id=user.id,
        action_type="RESERVATION_UPDATE",
        target_type="reservation",
        target_id=r.public_id,
        summary="Updated reservation",
        diff_json={"fields": sorted(list(data.keys()))},
        request=request,
    )

    return r


@router.post("/{reservation_id}/cancel")
def cancel_admin(reservation_id: str, request: Request, reason: str = "", db: Session = Depends(get_db), user=Depends(require_permissions(["RESERVATION_CANCEL"]))):
    r = db.get(Reservation, reservation_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    cancel_reservation(db, reservation=r, reason=reason)
    write_audit_log(
        db,
        actor_user_id=user.id,
        action_type="RESERVATION_CANCEL",
        target_type="reservation",
        target_id=r.public_id,
        summary="Cancelled reservation",
        diff_json=None,
        request=request,
    )
    return {"ok": True}
