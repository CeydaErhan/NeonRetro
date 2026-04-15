"""Visitor session routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import VisitorSession
from app.schemas import VisitorSessionCreate, VisitorSessionRead

router = APIRouter(tags=["visitor-sessions"])


@router.post("/visitor-sessions", response_model=VisitorSessionRead)
async def create_visitor_session(
    payload: VisitorSessionCreate, db: Session = Depends(get_db)
) -> VisitorSessionRead:
    """Store a new visitor session and return its identifier."""
    visitor_session = VisitorSession(
        user_agent=payload.user_agent,
        referrer=payload.referrer,
    )
    db.add(visitor_session)
    db.commit()
    db.refresh(visitor_session)
    return visitor_session
