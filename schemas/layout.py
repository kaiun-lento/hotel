from __future__ import annotations

from pydantic import BaseModel, Field


class VenueLayoutTemplateCreate(BaseModel):
    venue_id: str
    background_image_url: str = Field(min_length=0, max_length=1000)
    canvas_width: int = Field(default=1200, ge=1, le=10000)
    canvas_height: int = Field(default=800, ge=1, le=10000)
    metadata_json: dict = Field(default_factory=dict)


class VenueLayoutTemplateUpdate(BaseModel):
    background_image_url: str | None = Field(default=None, max_length=1000)
    canvas_width: int | None = Field(default=None, ge=1, le=10000)
    canvas_height: int | None = Field(default=None, ge=1, le=10000)
    metadata_json: dict | None = None


class VenueLayoutTemplateOut(BaseModel):
    id: str
    venue_id: str
    background_image_url: str
    canvas_width: int
    canvas_height: int
    metadata_json: dict

    class Config:
        from_attributes = True


class LayoutAssetCreate(BaseModel):
    venue_id: str | None = None
    asset_type: str = Field(default="TABLE", max_length=32)
    shape: str = Field(default="RECT", max_length=32)
    name: str = Field(default="", max_length=255)
    image_url: str = Field(default="", max_length=1000)
    default_width: int = Field(default=120, ge=1, le=5000)
    default_height: int = Field(default=80, ge=1, le=5000)
    active: bool = True
    metadata_json: dict = Field(default_factory=dict)


class LayoutAssetUpdate(BaseModel):
    venue_id: str | None = None
    asset_type: str | None = Field(default=None, max_length=32)
    shape: str | None = Field(default=None, max_length=32)
    name: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=1000)
    default_width: int | None = Field(default=None, ge=1, le=5000)
    default_height: int | None = Field(default=None, ge=1, le=5000)
    active: bool | None = None
    metadata_json: dict | None = None


class LayoutAssetOut(BaseModel):
    id: str
    venue_id: str | None
    asset_type: str
    shape: str
    name: str
    image_url: str
    default_width: int
    default_height: int
    active: bool
    metadata_json: dict

    class Config:
        from_attributes = True


class ReservationLayoutUpsert(BaseModel):
    # JSON: placed items, labels, seat assignment, etc.
    layout_json: dict = Field(default_factory=dict)
