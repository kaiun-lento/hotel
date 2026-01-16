from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_permissions
from app.models.venue import Venue
from app.schemas.venue import VenueCreate, VenueOut, VenueUpdate
from app.services.audit_service import write_audit_log

router = APIRouter()


@router.get("", response_model=list[VenueOut])
def list_venues(db: Session = Depends(get_db), user=Depends(require_permissions(["VENUE_MANAGE"]))):
    venues = db.execute(select(Venue).order_by(Venue.sort_order, Venue.name)).scalars().all()
    return venues


@router.post("", response_model=VenueOut)
def create_venue(payload: VenueCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["VENUE_MANAGE"]))):
    v = Venue(name=payload.name, sort_order=payload.sort_order, active=payload.active)
    db.add(v)
    db.commit()
    db.refresh(v)

    write_audit_log(db, actor_user_id=user.id, action_type="VENUE_CREATE", target_type="venue", target_id=v.id, summary="Created venue", request=request)
    return v


@router.patch("/{venue_id}", response_model=VenueOut)
def update_venue(venue_id: str, payload: VenueUpdate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["VENUE_MANAGE"]))):
    v = db.get(Venue, venue_id)
    if not v:
        raise HTTPException(status_code=404, detail="Not found")
    data = payload.dict(exclude_unset=True)
    for k, val in data.items():
        setattr(v, k, val)
    db.commit()
    db.refresh(v)

    write_audit_log(db, actor_user_id=user.id, action_type="VENUE_UPDATE", target_type="venue", target_id=v.id, summary="Updated venue", diff_json={"keys": sorted(list(data.keys()))}, request=request)
    return v


@router.delete("/{venue_id}")
def delete_venue(venue_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["VENUE_MANAGE"]))):
    v = db.get(Venue, venue_id)
    if not v:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(v)
    db.commit()

    write_audit_log(db, actor_user_id=user.id, action_type="VENUE_DELETE", target_type="venue", target_id=venue_id, summary="Deleted venue", request=request)
    return {"ok": True}
