from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginChallengeResponse, Verify2FARequest, TokenResponse, MeResponse
from app.services.auth_service import create_login_challenge, verify_login_challenge, get_user_permissions

router = APIRouter()


@router.post("/login", response_model=LoginChallengeResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    challenge_id = create_login_challenge(db, email=str(payload.email), password=payload.password, ip=ip, user_agent=ua)
    return LoginChallengeResponse(challenge_id=challenge_id)


@router.post("/verify", response_model=TokenResponse)
def verify_2fa(payload: Verify2FARequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    user = verify_login_challenge(db, challenge_id=payload.challenge_id, code=payload.code, ip=ip, user_agent=ua)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    perms = get_user_permissions(db, user.id) if not user.is_root_admin else ["*"]
    return MeResponse(user_id=user.id, email=user.email, name=user.name, is_root_admin=user.is_root_admin, permissions=perms)
