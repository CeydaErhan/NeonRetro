"""SQLAlchemy models for the Website & Advertisement Optimizer."""

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Application user with role-based access fields."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="analyst")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class VisitorSession(Base):
    """Visitor session used to group tracking events and ad interactions."""

    __tablename__ = "visitor_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    referrer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    visitor_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    events: Mapped[list["Event"]] = relationship("Event", back_populates="session", cascade="all, delete-orphan")
    impressions: Mapped[list["Impression"]] = relationship(
        "Impression", back_populates="session", cascade="all, delete-orphan"
    )


class Event(Base):
    """Tracked visitor event such as click, view, or conversion action."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("visitor_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    page: Mapped[str] = mapped_column(String(255), nullable=False)
    element: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=None)

    session: Mapped[VisitorSession] = relationship("VisitorSession", back_populates="events")


class Campaign(Base):
    """Marketing campaign configuration used to organize ads."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    target_page: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    ads: Mapped[list["Ad"]] = relationship("Ad", back_populates="campaign", cascade="all, delete-orphan")


class Ad(Base):
    """Advertisement unit belonging to a campaign."""

    __tablename__ = "ads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    target_page: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="ads")
    impressions: Mapped[list["Impression"]] = relationship(
        "Impression", back_populates="ad", cascade="all, delete-orphan"
    )


class Impression(Base):
    """Ad impression and optional click details."""

    __tablename__ = "impressions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ad_id: Mapped[int] = mapped_column(ForeignKey("ads.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("visitor_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    shown_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    clicked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    click_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ad: Mapped[Ad] = relationship("Ad", back_populates="impressions")
    session: Mapped[VisitorSession] = relationship("VisitorSession", back_populates="impressions")
