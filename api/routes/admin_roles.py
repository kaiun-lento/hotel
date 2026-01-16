from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_root_admin
from app.models.permission import Permission
from app.models.role import Role, RolePermission
from app.models.user import UserRole
from app.schemas.role import RoleCreate, RoleOut, RoleUpdate
from app.services.audit_service import write_audit_log

router = APIRouter()


@router.get("", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db), user=Depends(require_root_admin)):
    roles = db.execute(select(Role).order_by(Role.name)).scalars().all()
    out: list[RoleOut] = []
    for r in roles:
        perms = [rp.permission_code for rp in r.permissions]
        out.append(RoleOut(id=r.id, name=r.name, description=r.description, permission_codes=sorted(perms)))
    return out


@router.post("", response_model=RoleOut)
def create_role(payload: RoleCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_root_admin)):
    # Validate permissions exist
    if payload.permission_codes:
        existing = db.execute(select(Permission.code).where(Permission.code.in_(payload.permission_codes))).scalars().all()
        missing = set(payload.permission_codes) - set(existing)
        if missing:
            raise HTTPException(status_code=400, detail=f"Unknown permissions: {sorted(missing)}")

    role = Role(name=payload.name, description=payload.description or "", created_by_user_id=user.id)
    db.add(role)
    db.commit()
    db.refresh(role)

    for code in set(payload.permission_codes or []):
        db.add(RolePermission(role_id=role.id, permission_code=code))
    db.commit()
    db.refresh(role)

    write_audit_log(
        db,
        actor_user_id=user.id,
        action_type="ROLE_CREATE",
        target_type="role",
        target_id=role.id,
        summary=f"Created role {role.name}",
        diff_json={"permission_codes": sorted(set(payload.permission_codes or []))},
        request=request,
    )

    perms = [rp.permission_code for rp in role.permissions]
    return RoleOut(id=role.id, name=role.name, description=role.description, permission_codes=sorted(perms))


@router.get("/{role_id}", response_model=RoleOut)
def get_role(role_id: str, db: Session = Depends(get_db), user=Depends(require_root_admin)):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Not found")
    perms = [rp.permission_code for rp in role.permissions]
    return RoleOut(id=role.id, name=role.name, description=role.description, permission_codes=sorted(perms))


@router.patch("/{role_id}", response_model=RoleOut)
def update_role(role_id: str, payload: RoleUpdate, request: Request, db: Session = Depends(get_db), user=Depends(require_root_admin)):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Not found")

    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description

    if payload.permission_codes is not None:
        # Validate permissions exist
        existing = db.execute(select(Permission.code).where(Permission.code.in_(payload.permission_codes))).scalars().all()
        missing = set(payload.permission_codes) - set(existing)
        if missing:
            raise HTTPException(status_code=400, detail=f"Unknown permissions: {sorted(missing)}")

        current = {rp.permission_code for rp in role.permissions}
        desired = set(payload.permission_codes)
        to_add = desired - current
        to_remove = current - desired

        if to_remove:
            db.query(RolePermission).filter(RolePermission.role_id == role.id, RolePermission.permission_code.in_(list(to_remove))).delete(synchronize_session=False)
        for code in to_add:
            db.add(RolePermission(role_id=role.id, permission_code=code))

    db.commit()
    db.refresh(role)

    write_audit_log(
        db,
        actor_user_id=user.id,
        action_type="ROLE_UPDATE",
        target_type="role",
        target_id=role.id,
        summary=f"Updated role {role.name}",
        diff_json={"updated": True},
        request=request,
    )

    perms = [rp.permission_code for rp in role.permissions]
    return RoleOut(id=role.id, name=role.name, description=role.description, permission_codes=sorted(perms))


@router.delete("/{role_id}")
def delete_role(role_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_root_admin)):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Not found")

    # Prevent delete if assigned
    assigned = db.execute(select(UserRole).where(UserRole.role_id == role_id).limit(1)).first()
    if assigned:
        raise HTTPException(status_code=409, detail="Role is assigned to users")

    db.delete(role)
    db.commit()

    write_audit_log(
        db,
        actor_user_id=user.id,
        action_type="ROLE_DELETE",
        target_type="role",
        target_id=role_id,
        summary=f"Deleted role {role.name}",
        diff_json=None,
        request=request,
    )

    return {"ok": True}
