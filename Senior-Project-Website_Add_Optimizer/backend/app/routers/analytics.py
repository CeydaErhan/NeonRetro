"""Analytics reporting routes."""

from io import StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Ad, Campaign, Event, Impression, User, VisitorSession

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def analytics_summary(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, float | int]:
    """Return high-level analytics metrics across sessions, events, and ads."""
    session_total = db.scalar(select(func.count(VisitorSession.id)))
    event_total = db.scalar(select(func.count(Event.id)))
    ad_total = db.scalar(select(func.count(Ad.id)))
    impression_total = db.scalar(select(func.count(Impression.id)))
    click_total = db.scalar(select(func.count(Impression.id)).where(Impression.clicked.is_(True)))

    impressions = impression_total or 0
    clicks = click_total or 0
    ctr = (clicks / impressions) if impressions else 0.0

    return {
        "sessions": int(session_total or 0),
        "events": int(event_total or 0),
        "ads": int(ad_total or 0),
        "impressions": int(impressions),
        "clicks": int(clicks),
        "ctr": round(ctr, 4),
    }


@router.get("/export")
async def analytics_export(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> StreamingResponse:
    """Export campaign-level impression and click metrics as a CSV report."""
    stmt = (
        select(
            Campaign.id,
            Campaign.name,
            func.count(Impression.id).label("impressions"),
            func.count(Impression.id).filter(Impression.clicked.is_(True)).label("clicks"),
        )
        .select_from(Campaign)
        .join(Ad, Ad.campaign_id == Campaign.id, isouter=True)
        .join(Impression, Impression.ad_id == Ad.id, isouter=True)
        .group_by(Campaign.id, Campaign.name)
        .order_by(Campaign.id.asc())
    )
    rows = db.execute(stmt).all()

    buffer = StringIO()
    buffer.write("campaign_id,campaign_name,impressions,clicks,ctr\n")
    for campaign_id, campaign_name, impressions, clicks in rows:
        imp = int(impressions or 0)
        clk = int(clicks or 0)
        ctr = (clk / imp) if imp else 0.0
        buffer.write(f"{campaign_id},{campaign_name},{imp},{clk},{ctr:.4f}\n")

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics_export.csv"},
    )
