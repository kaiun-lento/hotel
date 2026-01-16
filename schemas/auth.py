from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginChallengeResponse(BaseModel):
    challenge_id: str
    message: str = "2FA code sent"


class Verify2FARequest(BaseModel):
    challenge_id: str
    code: str = Field(min_length=4, max_length=12)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user_id: str
    email: EmailStr
    name: str
    is_root_admin: bool
    permissions: list[str]
