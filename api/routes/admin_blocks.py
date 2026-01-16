from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_db, require_permissions
from app.models.calendar_block import CalendarBlock
from app.schemas.calendar_block import CalendarBlockCreate, CalendarBlockOut
from app.services.audit_service import write_audit_log

router = APIRouter()


class BulkBlockCreate(BaseModel):
    venue_ids: list[str] = Field(min_items=1)
    date_from: date
    date_to: date
    start_time: time
    end_time: time
    reason: str = Field(default="", max_length=255)


@router.get("", response_model=list[CalendarBlockOut])
def list_blocks(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    venue_id: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_permissions(["RULES_VIEW"])),
):
    q = select(CalendarBlock).order_by(CalendarBlock.start_at.desc())
    if from_:
        q = q.where(CalendarBlock.start_at >= from_)
    if to:
        q = q.where(CalendarBlock.end_at <= to)
    if venue_id:
        q = q.where(CalendarBlock.venue_id == venue_id)
    return db.execute(q.limit(1000)).scalars().all()


@router.post("", response_model=CalendarBlockOut)
def create_block(payload: CalendarBlockCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["CALENDAR_BLOCK_SINGLE"]))):
    if payload.start_at >= payload.end_at:
        raise HTTPException(status_code=400, detail="Invalid time range")

    b = CalendarBlock(venue_id=payload.venue_id, start_at=payload.start_at, end_at=payload.end_at, reason=payload.reason, created_by_user_id=user.id)
    db.add(b)
    db.commit()
    db.refresh(b)

    write_audit_log(db, actor_user_id=user.id, action_type="CALENDAR_BLOCK_SINGLE", target_type="block", target_id=b.id, summary="Created calendar block", request=request)
    return b


@router.post("/bulk")
def create_blocks_bulk(payload: BulkBlockCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["CALENDAR_BLOCK_BULK"]))):
    if payload.date_from > payload.date_to:
        raise HTTPException(status_code=400, detail="Invalid date range")
    if payload.start_time >= payload.end_time:
        raise HTTPException(status_code=400, detail="Invalid time range")

    app_settings = get_settings()
    tz = ZoneInfo(app_settings.timezone)

    created = 0
    d = payload.date_from
    while d <= payload.date_to:
        start_local = datetime.combine(d, payload.start_time).replace(tzinfo=tz)
        end_local = datetime.combine(d, payload.end_time).replace(tzinfo=tz)
        start_at = start_local.astimezone(ZoneInfo("UTC"))
        end_at = end_local.astimezone(ZoneInfo("UTC"))
        for vid in payload.venue_ids:
            db.add(CalendarBlock(venue_id=vid, start_at=start_at, end_at=end_at, reason=payload.reason, created_by_user_id=user.id))
            created += 1
        d = d + timedelta(days=1)

    db.commit()

    write_audit_log(
        db,
        actor_user_id=user.id,
        action_type="CALENDAR_BLOCK_BULK",
        target_type="block",
        target_id="bulk",
        summary="Created calendar blocks (bulk)",
        diff_json={"count": created, "from": str(payload.date_from), "to": str(payload.date_to)},
        request=request,
    )

    return {"ok": True, "created": created}


@router.delete("/{block_id}")
def delete_block(block_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["CALENDAR_BLOCK_SINGLE"]))):
    b = db.get(CalendarBlock, block_id)
    if not b:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(b)
    db.commit()

    write_audit_log(db, actor_user_id=user.id, action_type="CALENDAR_BLOCK_DELETE", target_type="block", target_id=block_id, summary="Deleted calendar block", request=request)
    return {"ok": True}
