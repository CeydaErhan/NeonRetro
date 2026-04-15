"""Recommendation route for ML-driven session-aware ad suggestions."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Event, User, VisitorSession
from ml.recommendation import get_recommendations as get_segment_recommendations
from ml.scoring import score_session

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("")
async def list_recommendations(
    session_id: int = Query(..., ge=1),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    """Return ML-ranked ads for the provided visitor session."""
    visitor_session = db.execute(select(VisitorSession).where(VisitorSession.id == session_id)).scalar_one_or_none()
    if visitor_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor session not found")

    click_count = int(
        db.scalar(select(func.count(Event.id)).where(Event.session_id == session_id, Event.type == "click")) or 0
    )

    session_end = visitor_session.ended_at or datetime.utcnow()
    dwell_time_seconds = max((session_end - visitor_session.started_at).total_seconds(), 0.0)
    segment = score_session(
        page_count=int(visitor_session.page_count or 0),
        click_count=click_count,
        dwell_time_seconds=dwell_time_seconds,
    )

    recommended_ads = get_segment_recommendations(segment=segment, db_session=db, limit=3)
    return [
        {
            "id": ad.id,
            "campaign_id": ad.campaign_id,
            "title": ad.title,
            "content": ad.content,
            "image_url": ad.image_url,
            "target_page": ad.target_page,
            "segment": segment,
        }
        for ad in recommended_ads
    ]
