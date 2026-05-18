"""Analytics reporting routes."""

from datetime import date, timedelta
from io import StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Ad, Campaign, Event, Impression, User, VisitorSession
from app.schemas import CampaignPerformanceRead, VisitorsByDayRead

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def analytics_summary(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, float | int]:
    """Return high-level analytics metrics across sessions, events, and ads."""
    session_total = db.scalar(select(func.count(VisitorSession.id)))
    event_total = db.scalar(select(func.count(Event.id)))
    page_view_total = db.scalar(select(func.count(Event.id)).where(Event.type.in_(["page_view", "pageview"])))
    ad_total = db.scalar(select(func.count(Ad.id)))
    impression_total = db.scalar(select(func.count(Impression.id)))
    click_total = db.scalar(select(func.count(Impression.id)).where(Impression.clicked.is_(True)))

    impressions = impression_total or 0
    clicks = click_total or 0
    ctr = (clicks / impressions) if impressions else 0.0

    return {
        "sessions": int(session_total or 0),
        "events": int(event_total or 0),
        "page_views": int(page_view_total or 0),
        "ads": int(ad_total or 0),
        "impressions": int(impressions),
        "clicks": int(clicks),
        "ctr": round(ctr, 4),
    }


@router.get("/visitors-by-day", response_model=list[VisitorsByDayRead])
async def visitors_by_day(
    days: int = 7,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VisitorsByDayRead]:
    """Return page-view counts grouped by day for the requested recent window."""
    days = max(1, min(days, 30))
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    stmt = (
        select(func.date(Event.timestamp).label("day"), func.count(Event.id).label("visitors"))
        .where(Event.type.in_(["page_view", "pageview"]))
        .where(func.date(Event.timestamp) >= start_date)
        .group_by(func.date(Event.timestamp))
        .order_by(func.date(Event.timestamp).asc())
    )
    rows = db.execute(stmt).all()
    counts = {str(day): int(visitors or 0) for day, visitors in rows}

    results: list[VisitorsByDayRead] = []
    for index in range(days):
        current_day = start_date + timedelta(days=index)
        results.append(
            VisitorsByDayRead(
                day=current_day.isoformat(),
                visitors=counts.get(current_day.isoformat(), 0),
            )
        )
    return results


@router.get("/export")
async def analytics_export(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> StreamingResponse:
    """Export campaign-level impression and click metrics as a CSV report."""
    rows = _campaign_performance_rows(db)

    buffer = StringIO()
    buffer.write("campaign_id,campaign_name,impressions,clicks,ctr\n")
    for row in rows:
        buffer.write(
            f"{row.campaign_id},{row.campaign_name},{row.impressions},{row.clicks},{row.ctr:.4f}\n"
        )

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics_export.csv"},
    )


def _campaign_performance_rows(db: Session) -> list[CampaignPerformanceRead]:
    """Return campaign-level impression, click, and CTR metrics."""
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
        .order_by(func.count(Impression.id).desc(), Campaign.id.asc())
    )
    rows = db.execute(stmt).all()

    performance_rows: list[CampaignPerformanceRead] = []
    for campaign_id, campaign_name, impressions, clicks in rows:
        imp = int(impressions or 0)
        clk = int(clicks or 0)
        ctr = (clk / imp) if imp else 0.0
        performance_rows.append(
            CampaignPerformanceRead(
                campaign_id=int(campaign_id),
                campaign_name=str(campaign_name),
                impressions=imp,
                clicks=clk,
                ctr=round(ctr, 4),
            )
        )
    return performance_rows


@router.get("/campaign-performance", response_model=list[CampaignPerformanceRead])
async def campaign_performance(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CampaignPerformanceRead]:
    """Return campaign-level ad performance for the business dashboard."""
    return _campaign_performance_rows(db)
