"""Event tracking routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Event, User
from app.schemas import EventCreate, EventRead

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/track", response_model=EventRead)
async def track_event(payload: EventCreate, db: Session = Depends(get_db)) -> EventRead:
    """Store a new visitor event payload."""
    data = payload.model_dump(by_alias=False)
    if data.get("timestamp") is None:
        data["timestamp"] = datetime.utcnow()
    event = Event(**data)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/list", response_model=list[EventRead])
async def list_events(
    session_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EventRead]:
    """List tracked events with optional session filtering and pagination."""
    stmt = select(Event).order_by(Event.timestamp.desc()).offset(offset).limit(limit)
    if session_id is not None:
        stmt = stmt.where(Event.session_id == session_id)
    result = db.execute(stmt)
    return list(result.scalars().all())
