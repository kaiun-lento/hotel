from __future__ import annotations

from typing import Any, Mapping

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

SENSITIVE_KEYS = {
    "password",
    "hashed_password",
    "phone",
    "phone_normalized",
    "phone_hash",
    "email",
    "email_normalized",
    "email_hash",
    "name",
    "customer_name",
}


def _sanitize(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        clean: dict[str, Any] = {}
        for k, v in obj.items():
            if k in SENSITIVE_KEYS:
                # Drop or mask sensitive value
                clean[k] = "<redacted>"
            else:
                clean[k] = _sanitize(v)
        return clean
    if isinstance(obj, (list, tuple)):
        return [ _sanitize(v) for v in obj ]
    return obj


def write_audit_log(
    db: Session,
    *,
    actor_user_id: str | None,
    action_type: str,
    target_type: str = "",
    target_id: str = "",
    summary: str = "",
    diff_json: Mapping[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    ip = ""
    ua = ""
    if request is not None:
        ip = request.client.host if request.client else ""
        ua = request.headers.get("user-agent", "")

    log = AuditLog(
        actor_user_id=actor_user_id,
        action_type=action_type,
        target_type=target_type,
        target_id=str(target_id),
        summary=summary,
        diff_json=_sanitize(dict(diff_json)) if diff_json is not None else None,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(log)
    db.commit()
