from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_root_admin
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.audit_service import write_audit_log
from app.services.auth_service import normalize_email

router = APIRouter()


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user=Depends(require_root_admin)):
    users = db.execute(select(User).order_by(User.email)).scalars().all()
    out: list[UserOut] = []
    for u in users:
        role_ids = [ur.role_id for ur in u.roles]
        out.append(UserOut(id=u.id, email=u.email, name=u.name, is_active=u.is_active, is_root_admin=u.is_root_admin, last_login_at=u.last_login_at, role_ids=role_ids))
    return out


@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_root_admin)):
    email = normalize_email(str(payload.email))
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    # Validate role ids
    if payload.role_ids:
        roles = db.execute(select(Role.id).where(Role.id.in_(payload.role_ids))).scalars().all()
        missing = set(payload.role_ids) - set(roles)
        if missing:
            raise HTTPException(status_code=400, detail=f"Unknown roles: {sorted(missing)}")

    u = User(email=email, name=payload.name, hashed_password=hash_password(payload.password), is_active=True, is_root_admin=False)
    db.add(u)
    db.commit()
    db.refresh(u)

    for rid in set(payload.role_ids or []):
        db.add(UserRole(user_id=u.id, role_id=rid))
    db.commit()
    db.refresh(u)

    write_audit_log(
        db,
        actor_user_id=user.id,
        action_type="USER_CREATE",
        target_type="user",
        target_id=u.id,
        summary="Created user",
        diff_json={"user_id": u.id, "role_count": len(set(payload.role_ids or []))},
        request=request,
    )

    role_ids = [ur.role_id for ur in u.roles]
    return UserOut(id=u.id, email=u.email, name=u.name, is_active=u.is_active, is_root_admin=u.is_root_admin, last_login_at=u.last_login_at, role_ids=role_ids)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db), user=Depends(require_root_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Not found")
    role_ids = [ur.role_id for ur in u.roles]
    return UserOut(id=u.id, email=u.email, name=u.name, is_active=u.is_active, is_root_admin=u.is_root_admin, last_login_at=u.last_login_at, role_ids=role_ids)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate, request: Request, db: Session = Depends(get_db), user=Depends(require_root_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Not found")

    if payload.email is not None:
        email = normalize_email(str(payload.email))
        dup = db.execute(select(User).where(User.email == email, User.id != u.id)).scalar_one_or_none()
        if dup:
            raise HTTPException(status_code=409, detail="Email already exists")
        u.email = email
    if payload.name is not None:
        u.name = payload.name
    if payload.is_active is not None:
        u.is_active = payload.is_active

    db.commit()

    write_audit_log(
        db,
        actor_user_id=user.id,
        action_type="USER_UPDATE",
        target_type="user",
        target_id=u.id,
        summary="Updated user",
        diff_json={"updated": True},
        request=request,
    )

    role_ids = [ur.role_id for ur in u.roles]
    return UserOut(id=u.id, email=u.email, name=u.name, is_active=u.is_active, is_root_admin=u.is_root_admin, last_login_at=u.last_login_at, role_ids=role_ids)


@router.put("/{user_id}/roles", response_model=UserOut)
def replace_user_roles(user_id: str, role_ids: list[str], request: Request, db: Session = Depends(get_db), user=Depends(require_root_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Not found")

    if role_ids:
        roles = db.execute(select(Role.id).where(Role.id.in_(role_ids))).scalars().all()
        missing = set(role_ids) - set(roles)
        if missing:
            raise HTTPException(status_code=400, detail=f"Unknown roles: {sorted(missing)}")

    # Replace
    db.query(UserRole).filter(UserRole.user_id == u.id).delete(synchronize_session=False)
    for rid in set(role_ids or []):
        db.add(UserRole(user_id=u.id, role_id=rid))
    db.commit()
    db.refresh(u)

    write_audit_log(
        db,
        actor_user_id=user.id,
        action_type="USER_ROLE_ASSIGN",
        target_type="user",
        target_id=u.id,
        summary="Replaced user roles",
        diff_json={"role_count": len(set(role_ids or []))},
        request=request,
    )

    role_ids_out = [ur.role_id for ur in u.roles]
    return UserOut(id=u.id, email=u.email, name=u.name, is_active=u.is_active, is_root_admin=u.is_root_admin, last_login_at=u.last_login_at, role_ids=role_ids_out)


@router.post("/{user_id}/root-admin/grant")
def grant_root_admin(user_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_root_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Not found")
    u.is_root_admin = True
    db.commit()

    write_audit_log(db, actor_user_id=user.id, action_type="USER_GRANT_ROOT", target_type="user", target_id=u.id, summary="Granted root admin", request=request)
    return {"ok": True}


@router.post("/{user_id}/root-admin/revoke")
def revoke_root_admin(user_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_root_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Not found")

    if not u.is_root_admin:
        return {"ok": True}

    # Ensure at least one root admin remains
    root_count = db.execute(select(User).where(User.is_root_admin == True)).scalars().all()
    if len(root_count) <= 1:
        raise HTTPException(status_code=409, detail="At least one Root Admin must remain")

    u.is_root_admin = False
    db.commit()

    write_audit_log(db, actor_user_id=user.id, action_type="USER_REVOKE_ROOT", target_type="user", target_id=u.id, summary="Revoked root admin", request=request)
    return {"ok": True}
