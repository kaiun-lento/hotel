from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_permissions
from app.models.layout import LayoutAsset, ReservationLayout, VenueLayoutTemplate
from app.models.reservation import Reservation
from app.schemas.layout import (
    LayoutAssetCreate,
    LayoutAssetOut,
    LayoutAssetUpdate,
    ReservationLayoutUpsert,
    VenueLayoutTemplateCreate,
    VenueLayoutTemplateOut,
    VenueLayoutTemplateUpdate,
)
from app.services.audit_service import write_audit_log

router = APIRouter()


@router.get("/templates", response_model=list[VenueLayoutTemplateOut])
def list_templates(db: Session = Depends(get_db), user=Depends(require_permissions(["LAYOUT_MANAGE"]))):
    return db.execute(select(VenueLayoutTemplate).order_by(VenueLayoutTemplate.created_at.desc())).scalars().all()


@router.post("/templates", response_model=VenueLayoutTemplateOut)
def create_template(payload: VenueLayoutTemplateCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["LAYOUT_MANAGE"]))):
    # One template per venue (unique constraint)
    existing = db.execute(select(VenueLayoutTemplate).where(VenueLayoutTemplate.venue_id == payload.venue_id)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Template already exists for this venue")
    t = VenueLayoutTemplate(
        venue_id=payload.venue_id,
        background_image_url=payload.background_image_url,
        canvas_width=payload.canvas_width,
        canvas_height=payload.canvas_height,
        metadata_json=payload.metadata_json,
    )
    db.add(t)
    db.commit()
    db.refresh(t)

    write_audit_log(db, actor_user_id=user.id, action_type="LAYOUT_TEMPLATE_CREATE", target_type="layout_template", target_id=t.id, summary="Created venue layout template", request=request)
    return t


@router.patch("/templates/{template_id}", response_model=VenueLayoutTemplateOut)
def update_template(template_id: str, payload: VenueLayoutTemplateUpdate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["LAYOUT_MANAGE"]))):
    t = db.get(VenueLayoutTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    write_audit_log(db, actor_user_id=user.id, action_type="LAYOUT_TEMPLATE_UPDATE", target_type="layout_template", target_id=t.id, summary="Updated venue layout template", diff_json={"keys": sorted(list(data.keys()))}, request=request)
    return t


@router.delete("/templates/{template_id}")
def delete_template(template_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["LAYOUT_MANAGE"]))):
    t = db.get(VenueLayoutTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(t)
    db.commit()
    write_audit_log(db, actor_user_id=user.id, action_type="LAYOUT_TEMPLATE_DELETE", target_type="layout_template", target_id=template_id, summary="Deleted venue layout template", request=request)
    return {"ok": True}


@router.get("/assets", response_model=list[LayoutAssetOut])
def list_assets(venue_id: str | None = None, db: Session = Depends(get_db), user=Depends(require_permissions(["LAYOUT_MANAGE"]))):
    q = select(LayoutAsset).order_by(LayoutAsset.created_at.desc())
    if venue_id:
        q = q.where((LayoutAsset.venue_id == None) | (LayoutAsset.venue_id == venue_id))
    return db.execute(q).scalars().all()


@router.post("/assets", response_model=LayoutAssetOut)
def create_asset(payload: LayoutAssetCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["LAYOUT_MANAGE"]))):
    a = LayoutAsset(
        venue_id=payload.venue_id,
        asset_type=payload.asset_type,
        shape=payload.shape,
        name=payload.name,
        image_url=payload.image_url,
        default_width=payload.default_width,
        default_height=payload.default_height,
        active=payload.active,
        metadata_json=payload.metadata_json,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    write_audit_log(db, actor_user_id=user.id, action_type="LAYOUT_ASSET_CREATE", target_type="layout_asset", target_id=a.id, summary="Created layout asset", request=request)
    return a


@router.patch("/assets/{asset_id}", response_model=LayoutAssetOut)
def update_asset(asset_id: str, payload: LayoutAssetUpdate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["LAYOUT_MANAGE"]))):
    a = db.get(LayoutAsset, asset_id)
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    write_audit_log(db, actor_user_id=user.id, action_type="LAYOUT_ASSET_UPDATE", target_type="layout_asset", target_id=a.id, summary="Updated layout asset", diff_json={"keys": sorted(list(data.keys()))}, request=request)
    return a


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["LAYOUT_MANAGE"]))):
    a = db.get(LayoutAsset, asset_id)
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(a)
    db.commit()
    write_audit_log(db, actor_user_id=user.id, action_type="LAYOUT_ASSET_DELETE", target_type="layout_asset", target_id=asset_id, summary="Deleted layout asset", request=request)
    return {"ok": True}


@router.put("/reservations/{reservation_id}/layout")
def upsert_reservation_layout(
    reservation_id: str,
    payload: ReservationLayoutUpsert,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permissions(["RESERVATION_EDIT"])),
):
    r = db.get(Reservation, reservation_id)
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")

    existing = db.execute(select(ReservationLayout).where(ReservationLayout.reservation_id == reservation_id)).scalar_one_or_none()
    if existing is None:
        existing = ReservationLayout(reservation_id=reservation_id, layout_json=payload.layout_json)
        db.add(existing)
    else:
        existing.layout_json = payload.layout_json

    db.commit()

    write_audit_log(db, actor_user_id=user.id, action_type="RESERVATION_LAYOUT_UPSERT", target_type="reservation", target_id=r.public_id, summary="Updated reservation layout", request=request)
    return {"ok": True}
