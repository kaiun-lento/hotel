from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_permissions
from app.schemas.settings import SettingsOut, SettingsUpdate
from app.services.audit_service import write_audit_log
from app.services.settings_service import get_or_create_settings

router = APIRouter()


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), user=Depends(require_permissions(["SETTINGS_MANAGE"]))):
    return get_or_create_settings(db)


@router.patch("", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["SETTINGS_MANAGE"]))):
    s = get_or_create_settings(db)
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)

    write_audit_log(
        db,
        actor_user_id=user.id,
        action_type="SETTINGS_UPDATE",
        target_type="settings",
        target_id="1",
        summary="Updated settings",
        diff_json={"keys": sorted(list(data.keys()))},
        request=request,
    )
    return s
