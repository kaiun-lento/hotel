from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_permissions
from app.models.menu import MenuCategory, MenuItem, MenuItemPhoto
from app.schemas.menu import (
    MenuCategoryCreate,
    MenuCategoryOut,
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
    MenuPhotoCreate,
    MenuPhotoOut,
)
from app.services.audit_service import write_audit_log

router = APIRouter()


@router.get("/categories", response_model=list[MenuCategoryOut])
def list_categories(db: Session = Depends(get_db), user=Depends(require_permissions(["MENU_MANAGE"]))):
    return db.execute(select(MenuCategory).order_by(MenuCategory.sort_order, MenuCategory.name)).scalars().all()


@router.post("/categories", response_model=MenuCategoryOut)
def create_category(payload: MenuCategoryCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["MENU_MANAGE"]))):
    c = MenuCategory(name=payload.name, sort_order=payload.sort_order, active=payload.active)
    db.add(c)
    db.commit()
    db.refresh(c)
    write_audit_log(db, actor_user_id=user.id, action_type="MENU_CATEGORY_CREATE", target_type="menu_category", target_id=c.id, summary="Created menu category", request=request)
    return c


@router.patch("/categories/{category_id}", response_model=MenuCategoryOut)
def update_category(category_id: str, payload: MenuCategoryCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["MENU_MANAGE"]))):
    c = db.get(MenuCategory, category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    c.name = payload.name
    c.sort_order = payload.sort_order
    c.active = payload.active
    db.commit()
    db.refresh(c)
    write_audit_log(db, actor_user_id=user.id, action_type="MENU_CATEGORY_UPDATE", target_type="menu_category", target_id=c.id, summary="Updated menu category", request=request)
    return c


@router.delete("/categories/{category_id}")
def delete_category(category_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["MENU_MANAGE"]))):
    c = db.get(MenuCategory, category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(c)
    db.commit()
    write_audit_log(db, actor_user_id=user.id, action_type="MENU_CATEGORY_DELETE", target_type="menu_category", target_id=category_id, summary="Deleted menu category", request=request)
    return {"ok": True}


@router.get("/items", response_model=list[MenuItemOut])
def list_items(category_id: str | None = None, db: Session = Depends(get_db), user=Depends(require_permissions(["MENU_MANAGE"]))):
    q = select(MenuItem).order_by(MenuItem.created_at.desc())
    if category_id:
        q = q.where(MenuItem.category_id == category_id)
    return db.execute(q).scalars().all()


@router.post("/items", response_model=MenuItemOut)
def create_item(payload: MenuItemCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["MENU_MANAGE"]))):
    if not db.get(MenuCategory, payload.category_id):
        raise HTTPException(status_code=400, detail="Unknown category")
    it = MenuItem(category_id=payload.category_id, name=payload.name, description=payload.description or "", price=payload.price, active=payload.active)
    db.add(it)
    db.commit()
    db.refresh(it)
    write_audit_log(db, actor_user_id=user.id, action_type="MENU_ITEM_CREATE", target_type="menu_item", target_id=it.id, summary="Created menu item", request=request)
    return it


@router.patch("/items/{item_id}", response_model=MenuItemOut)
def update_item(item_id: str, payload: MenuItemUpdate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["MENU_MANAGE"]))):
    it = db.get(MenuItem, item_id)
    if not it:
        raise HTTPException(status_code=404, detail="Not found")
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(it, k, v)
    db.commit()
    db.refresh(it)
    write_audit_log(db, actor_user_id=user.id, action_type="MENU_ITEM_UPDATE", target_type="menu_item", target_id=it.id, summary="Updated menu item", diff_json={"keys": sorted(list(data.keys()))}, request=request)
    return it


@router.delete("/items/{item_id}")
def delete_item(item_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["MENU_MANAGE"]))):
    it = db.get(MenuItem, item_id)
    if not it:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(it)
    db.commit()
    write_audit_log(db, actor_user_id=user.id, action_type="MENU_ITEM_DELETE", target_type="menu_item", target_id=item_id, summary="Deleted menu item", request=request)
    return {"ok": True}


@router.post("/items/{item_id}/photos", response_model=MenuPhotoOut)
def add_photo(item_id: str, payload: MenuPhotoCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["MENU_MANAGE"]))):
    it = db.get(MenuItem, item_id)
    if not it:
        raise HTTPException(status_code=404, detail="Not found")
    ph = MenuItemPhoto(menu_item_id=item_id, url=payload.url, alt_text=payload.alt_text or "")
    db.add(ph)
    db.commit()
    db.refresh(ph)
    write_audit_log(db, actor_user_id=user.id, action_type="MENU_PHOTO_ADD", target_type="menu_photo", target_id=ph.id, summary="Added menu photo", request=request)
    return ph


@router.delete("/photos/{photo_id}")
def delete_photo(photo_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["MENU_MANAGE"]))):
    ph = db.get(MenuItemPhoto, photo_id)
    if not ph:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(ph)
    db.commit()
    write_audit_log(db, actor_user_id=user.id, action_type="MENU_PHOTO_DELETE", target_type="menu_photo", target_id=photo_id, summary="Deleted menu photo", request=request)
    return {"ok": True}
