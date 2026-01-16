from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select

from app.models.menu import MenuCategory, MenuItem, MenuItemPhoto
from app.models.venue import Venue
from app.models.layout import VenueLayoutTemplate, LayoutAsset, ReservationLayout


from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.availability import AvailabilityResponse, AvailabilityBlock
from app.schemas.reservation import (
    PublicReservationCreate,
    PublicReservationCreated,
    PublicReservationLookupRequest,
    PublicReservationCancelRequest,
    ReservationOut,
)
from app.schemas.layout import ReservationLayoutUpsert

from app.services.audit_service import write_audit_log
from app.services.availability_service import compute_public_availability
from app.services.reservation_service import (
    create_reservation_public,
    lookup_reservation_by_public_id_and_phone,
    get_reservation_by_token,
    cancel_reservation,
)
from app.services.captcha import verify_captcha

router = APIRouter()



@router.get('/venues')
def list_public_venues(db: Session = Depends(get_db)):
    venues = db.execute(select(Venue).where(Venue.active == True).order_by(Venue.sort_order, Venue.name)).scalars().all()
    return [{"id": v.id, "name": v.name} for v in venues]


@router.get('/menu')
def list_public_menu(db: Session = Depends(get_db)):
    # Returns active categories with active items and photos
    cats = db.execute(select(MenuCategory).where(MenuCategory.active == True).order_by(MenuCategory.sort_order, MenuCategory.name)).scalars().all()
    items = db.execute(select(MenuItem).where(MenuItem.active == True)).scalars().all()
    photos = db.execute(select(MenuItemPhoto)).scalars().all()

    photo_by_item: dict[str, list[dict]] = {}
    for ph in photos:
        photo_by_item.setdefault(ph.menu_item_id, []).append({"id": ph.id, "url": ph.url, "alt_text": ph.alt_text})

    items_by_cat: dict[str, list[dict]] = {}
    for it in items:
        items_by_cat.setdefault(it.category_id, []).append({
            "id": it.id,
            "name": it.name,
            "description": it.description,
            "price": it.price,
            "photos": photo_by_item.get(it.id, []),
        })

    return [
        {
            "id": c.id,
            "name": c.name,
            "items": items_by_cat.get(c.id, []),
        }
        for c in cats
    ]




@router.get('/venues/{venue_id}/layout')
def get_public_layout(venue_id: str, db: Session = Depends(get_db)):
    template = db.execute(select(VenueLayoutTemplate).where(VenueLayoutTemplate.venue_id == venue_id)).scalar_one_or_none()
    assets = db.execute(
        select(LayoutAsset).where(
            LayoutAsset.active == True,
            (LayoutAsset.venue_id == None) | (LayoutAsset.venue_id == venue_id),
        )
    ).scalars().all()

    return {
        "template": {
            "id": template.id,
            "venue_id": template.venue_id,
            "background_image_url": template.background_image_url,
            "canvas_width": template.canvas_width,
            "canvas_height": template.canvas_height,
            "metadata_json": template.metadata_json,
        } if template else None,
        "assets": [
            {
                "id": a.id,
                "venue_id": a.venue_id,
                "asset_type": a.asset_type,
                "shape": a.shape,
                "name": a.name,
                "image_url": a.image_url,
                "default_width": a.default_width,
                "default_height": a.default_height,
                "metadata_json": a.metadata_json,
            }
            for a in assets
        ],
    }


@router.put('/r/{token}/layout')
def update_layout_by_token(token: str, payload: ReservationLayoutUpsert, request: Request, db: Session = Depends(get_db)):
    r = get_reservation_by_token(db, token_raw=token)
    existing = db.execute(select(ReservationLayout).where(ReservationLayout.reservation_id == r.id)).scalar_one_or_none()
    if existing is None:
        existing = ReservationLayout(reservation_id=r.id, layout_json=payload.layout_json)
        db.add(existing)
    else:
        existing.layout_json = payload.layout_json
    db.commit()

    write_audit_log(
        db,
        actor_user_id=None,
        action_type='PUBLIC_RESERVATION_LAYOUT_UPSERT',
        target_type='reservation',
        target_id=r.public_id,
        summary='Updated layout (token)',
        diff_json=None,
        request=request,
    )

    return {"ok": True}

@router.get("/availability", response_model=AvailabilityResponse)
async def availability(
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db),
):
    blocks = compute_public_availability(db, from_date=from_date, to_date=to_date)
    return AvailabilityResponse(blocks=[AvailabilityBlock(**b) for b in blocks])


@router.post("/reservations", response_model=PublicReservationCreated)
async def create_reservation(payload: PublicReservationCreate, request: Request, db: Session = Depends(get_db)):
    # Optional CAPTCHA
    ip = request.client.host if request.client else None
    ok = await verify_captcha(payload.captcha_token, remote_ip=ip)
    if not ok:
        raise HTTPException(status_code=400, detail="CAPTCHA failed")

    if not payload.consent_accepted:
        raise HTTPException(status_code=400, detail="Consent required")

    r = create_reservation_public(
        db,
        venue_id=payload.venue_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        people_count=payload.people_count,
        booking_type=payload.booking_type,
        banquet_name=payload.banquet_name,
        desired_time_text=payload.desired_time_text,
        customer_name=payload.customer_name,
        phone=payload.phone,
        email=str(payload.email),
        menu_selections=[s.dict() for s in payload.menu_selections],
        consent_version=payload.consent_version,
    )

    write_audit_log(
        db,
        actor_user_id=None,
        action_type="PUBLIC_RESERVATION_CREATE",
        target_type="reservation",
        target_id=r.public_id,
        summary="Public reservation created",
        diff_json={"public_id": r.public_id, "venue_id": r.venue_id},
        request=request,
    )

    return PublicReservationCreated(public_id=r.public_id, message="仮予約を受け付けました。メールをご確認ください。")


@router.post("/reservations/lookup", response_model=ReservationOut)
def lookup(payload: PublicReservationLookupRequest, db: Session = Depends(get_db)):
    r = lookup_reservation_by_public_id_and_phone(db, public_id=payload.public_id, phone=payload.phone)
    return ReservationOut(
        public_id=r.public_id,
        venue_id=r.venue_id,
        start_at=r.start_at,
        end_at=r.end_at,
        people_count=r.people_count,
        booking_type=r.booking_type,
        banquet_name=r.banquet_name,
        status=r.status,
        desired_time_text=r.desired_time_text,
        menu_selections=[],
    )


@router.post("/reservations/{public_id}/cancel")
def cancel_by_id(public_id: str, payload: PublicReservationCancelRequest, request: Request, db: Session = Depends(get_db)):
    r = lookup_reservation_by_public_id_and_phone(db, public_id=public_id, phone=payload.phone)
    cancel_reservation(db, reservation=r, reason=payload.reason)

    write_audit_log(
        db,
        actor_user_id=None,
        action_type="PUBLIC_RESERVATION_CANCEL",
        target_type="reservation",
        target_id=r.public_id,
        summary="Public reservation cancelled",
        diff_json=None,
        request=request,
    )

    return {"ok": True}


@router.get("/r/{token}", response_model=ReservationOut)
def view_by_token(token: str, db: Session = Depends(get_db)):
    r = get_reservation_by_token(db, token_raw=token)
    return ReservationOut(
        public_id=r.public_id,
        venue_id=r.venue_id,
        start_at=r.start_at,
        end_at=r.end_at,
        people_count=r.people_count,
        booking_type=r.booking_type,
        banquet_name=r.banquet_name,
        status=r.status,
        desired_time_text=r.desired_time_text,
        menu_selections=[],
    )


@router.post("/r/{token}/cancel")
def cancel_by_token(token: str, request: Request, reason: str = "", db: Session = Depends(get_db)):
    r = get_reservation_by_token(db, token_raw=token)
    cancel_reservation(db, reservation=r, reason=reason)

    write_audit_log(
        db,
        actor_user_id=None,
        action_type="PUBLIC_RESERVATION_CANCEL_TOKEN",
        target_type="reservation",
        target_id=r.public_id,
        summary="Public reservation cancelled (token)",
        diff_json=None,
        request=request,
    )
    return {"ok": True}
