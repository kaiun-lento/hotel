from __future__ import annotations

import hashlib
import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.auth_event import AuthEvent
from app.models.login_challenge import LoginChallenge
from app.models.role import RolePermission
from app.models.user import User, UserRole
from app.services.mailer import send_email


def normalize_phone(phone: str) -> str:
    # Keep digits only
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits


def mask_phone(phone_normalized: str) -> str:
    # e.g. 09012341234 -> 090****1234
    if len(phone_normalized) <= 4:
        return "*" * len(phone_normalized)
    head = phone_normalized[:3]
    tail = phone_normalized[-4:]
    middle = "*" * max(0, len(phone_normalized) - len(head) - len(tail))
    return f"{head}{middle}{tail}"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def mask_email(email: str) -> str:
    try:
        local, domain = email.split("@", 1)
    except ValueError:
        return "***"
    if len(local) <= 1:
        masked_local = "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 1)
    return f"{masked_local}@{domain}"


def hash_pii(value: str) -> str:
    settings = get_settings()
    salted = (settings.secret_key + "|" + value).encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def generate_public_id() -> str:
    # Example: R-20260116-8F3K2
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"R-{date_part}-{rand}"


def generate_otp_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def get_user_permissions(db: Session, user_id: str) -> list[str]:
    # Join user_roles -> role_permissions
    q = (
        select(RolePermission.permission_code)
        .select_from(UserRole)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
    )
    rows = db.execute(q).all()
    return sorted({r[0] for r in rows})


def create_login_challenge(db: Session, *, email: str, password: str, ip: str = "", user_agent: str = "") -> str:
    email_norm = normalize_email(email)
    user = db.execute(select(User).where(User.email == email_norm)).scalar_one_or_none()

    if not user or not user.is_active:
        db.add(AuthEvent(user_id=user.id if user else None, event_type="LOGIN_FAIL", ip_address=ip, user_agent=user_agent, failure_reason="user_not_found_or_inactive"))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(password, user.hashed_password):
        db.add(AuthEvent(user_id=user.id, event_type="LOGIN_FAIL", ip_address=ip, user_agent=user_agent, failure_reason="bad_password"))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Password OK: issue 2FA challenge
    code = generate_otp_code(6)
    code_hash = hash_password(code)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    challenge = LoginChallenge(user_id=user.id, code_hash=code_hash, expires_at=expires_at, attempts=0, max_attempts=5, is_used=False)
    db.add(challenge)
    db.add(AuthEvent(user_id=user.id, event_type="LOGIN_2FA_SENT", ip_address=ip, user_agent=user_agent, failure_reason=""))
    db.commit()

    # Send email
    subject = "Your login code"
    body = f"Your one-time login code is: {code}\n\nThis code expires in 10 minutes."
    try:
        send_email(user.email, subject, body)
    except Exception as e:
        # If mail fails, invalidate the challenge
        challenge.is_used = True
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to send 2FA code") from e

    return challenge.id


def verify_login_challenge(db: Session, *, challenge_id: str, code: str, ip: str = "", user_agent: str = "") -> User:
    challenge = db.get(LoginChallenge, challenge_id)
    if not challenge or challenge.is_used:
        db.add(AuthEvent(user_id=None, event_type="LOGIN_FAIL", ip_address=ip, user_agent=user_agent, failure_reason="invalid_challenge"))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired challenge")

    if datetime.now(timezone.utc) > challenge.expires_at:
        challenge.is_used = True
        db.add(AuthEvent(user_id=challenge.user_id, event_type="LOGIN_FAIL", ip_address=ip, user_agent=user_agent, failure_reason="challenge_expired"))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired challenge")

    if challenge.attempts >= challenge.max_attempts:
        challenge.is_used = True
        db.add(AuthEvent(user_id=challenge.user_id, event_type="LOGIN_FAIL", ip_address=ip, user_agent=user_agent, failure_reason="too_many_attempts"))
        db.commit()
        raise HTTPException(status_code=401, detail="Too many attempts")

    if not verify_password(code, challenge.code_hash):
        challenge.attempts += 1
        db.add(AuthEvent(user_id=challenge.user_id, event_type="LOGIN_FAIL", ip_address=ip, user_agent=user_agent, failure_reason="bad_2fa_code"))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid code")

    # Success
    challenge.is_used = True
    user = db.get(User, challenge.user_id)
    if not user:
        db.add(AuthEvent(user_id=None, event_type="LOGIN_FAIL", ip_address=ip, user_agent=user_agent, failure_reason="user_missing"))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid")

    user.last_login_at = datetime.now(timezone.utc)
    db.add(AuthEvent(user_id=user.id, event_type="LOGIN_SUCCESS", ip_address=ip, user_agent=user_agent, failure_reason=""))
    db.commit()

    return user
