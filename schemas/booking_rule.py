from __future__ import annotations

from pydantic import BaseModel, Field


class BookingRuleCreate(BaseModel):
    rule_type: str = Field(min_length=1, max_length=64)
    scope_type: str = "ALL"
    scope_id: str = ""
    params_json: dict = Field(default_factory=dict)
    is_active: bool = True


class BookingRuleUpdate(BaseModel):
    rule_type: str | None = Field(default=None, min_length=1, max_length=64)
    scope_type: str | None = None
    scope_id: str | None = None
    params_json: dict | None = None
    is_active: bool | None = None


class BookingRuleOut(BaseModel):
    id: str
    rule_type: str
    scope_type: str
    scope_id: str
    params_json: dict
    is_active: bool

    class Config:
        from_attributes = True
