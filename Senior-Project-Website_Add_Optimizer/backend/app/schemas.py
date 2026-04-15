"""Pydantic v2 schemas used by API routes."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Shared user fields."""

    email: EmailStr
    role: str


class UserCreate(UserBase):
    """Schema to create a user account."""

    password: str = Field(min_length=8)


class UserRead(UserBase):
    """Schema returned when reading user data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class LoginRequest(BaseModel):
    """Credentials payload for login endpoint."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response schema."""

    access_token: str
    token_type: str = "bearer"


class VisitorSessionCreate(BaseModel):
    """Schema to create a visitor session."""

    user_agent: str
    referrer: str


class VisitorSessionRead(BaseModel):
    """Schema returned when reading visitor session data."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class EventBase(BaseModel):
    """Shared event tracking fields."""

    session_id: int
    type: str
    page: str
    element: str | None = None
    timestamp: datetime | None = None


class EventCreate(EventBase):
    """Schema to create an event record."""

    metadata_json: dict | None = Field(default=None, alias="metadata")


class EventRead(EventBase):
    """Schema returned when reading event records."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    metadata: dict | None = Field(default=None, validation_alias="metadata_json")


class CampaignBase(BaseModel):
    """Shared campaign fields."""

    name: str
    start_date: date
    end_date: date
    status: str
    target_page: str


class CampaignCreate(CampaignBase):
    """Schema to create a campaign."""


class CampaignUpdate(BaseModel):
    """Schema to update campaign fields."""

    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    target_page: str | None = None


class CampaignRead(CampaignBase):
    """Schema returned when reading campaign records."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class AdBase(BaseModel):
    """Shared ad fields."""

    campaign_id: int
    title: str
    content: str
    image_url: str | None = None
    target_page: str


class AdCreate(AdBase):
    """Schema to create an ad."""


class AdUpdate(BaseModel):
    """Schema to update ad fields."""

    campaign_id: int | None = None
    title: str | None = None
    content: str | None = None
    image_url: str | None = None
    target_page: str | None = None


class AdRead(AdBase):
    """Schema returned when reading ad records."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class ImpressionBase(BaseModel):
    """Shared impression fields."""

    ad_id: int
    session_id: int
    shown_at: datetime | None = None
    clicked: bool = False
    click_time: datetime | None = None


class ImpressionCreate(ImpressionBase):
    """Schema to create an impression."""


class ImpressionRead(ImpressionBase):
    """Schema returned when reading impression records."""

    model_config = ConfigDict(from_attributes=True)

    id: int
