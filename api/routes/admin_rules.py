from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_permissions
from app.models.booking_rule import BookingRule
from app.schemas.booking_rule import BookingRuleCreate, BookingRuleOut, BookingRuleUpdate
from app.services.audit_service import write_audit_log

router = APIRouter()


@router.get("", response_model=list[BookingRuleOut])
def list_rules(db: Session = Depends(get_db), user=Depends(require_permissions(["RULES_VIEW"]))):
    rules = db.execute(select(BookingRule).order_by(BookingRule.created_at.desc())).scalars().all()
    return rules


@router.post("", response_model=BookingRuleOut)
def create_rule(payload: BookingRuleCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["RULES_MANAGE"]))):
    r = BookingRule(rule_type=payload.rule_type, scope_type=payload.scope_type, scope_id=payload.scope_id, params_json=payload.params_json, is_active=payload.is_active, created_by_user_id=user.id)
    db.add(r)
    db.commit()
    db.refresh(r)

    write_audit_log(db, actor_user_id=user.id, action_type="RULE_CREATE", target_type="rule", target_id=r.id, summary="Created booking rule", request=request)
    return r


@router.patch("/{rule_id}", response_model=BookingRuleOut)
def update_rule(rule_id: str, payload: BookingRuleUpdate, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["RULES_MANAGE"]))):
    r = db.get(BookingRule, rule_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)

    write_audit_log(db, actor_user_id=user.id, action_type="RULE_UPDATE", target_type="rule", target_id=r.id, summary="Updated booking rule", diff_json={"keys": sorted(list(data.keys()))}, request=request)
    return r


@router.delete("/{rule_id}")
def delete_rule(rule_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permissions(["RULES_MANAGE"]))):
    r = db.get(BookingRule, rule_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(r)
    db.commit()

    write_audit_log(db, actor_user_id=user.id, action_type="RULE_DELETE", target_type="rule", target_id=rule_id, summary="Deleted booking rule", request=request)
    return {"ok": True}
