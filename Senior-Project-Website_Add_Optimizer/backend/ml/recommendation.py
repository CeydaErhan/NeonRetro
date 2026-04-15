"""Recommendation helpers for engagement-based ad selection."""

from __future__ import annotations

from datetime import date

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.orm import Session

from app.models import Ad, Campaign, Impression


def get_recommendations(segment: int, db_session: Session, limit: int = 3) -> list[Ad]:
    """Return ads ordered according to the engagement segment strategy."""
    today = date.today()

    impressions_count = func.count(Impression.id)
    clicks_count = func.sum(case((Impression.clicked.is_(True), 1), else_=0))
    ctr_value = func.coalesce(
        func.sum(case((Impression.clicked.is_(True), 1.0), else_=0.0)) / func.nullif(func.count(Impression.id), 0),
        0.0,
    )

    stmt = (
        select(Ad)
        .join(Campaign, Campaign.id == Ad.campaign_id)
        .join(Impression, Impression.ad_id == Ad.id, isouter=True)
        .where(
            and_(
                Campaign.status == "active",
                Campaign.start_date <= today,
                Campaign.end_date >= today,
            )
        )
        .group_by(Ad.id)
    )

    if segment == 0:
        stmt = stmt.order_by(Ad.id.desc())
    elif segment == 1:
        stmt = stmt.order_by(desc(impressions_count), Ad.id.desc())
    else:
        stmt = stmt.order_by(desc(ctr_value), desc(clicks_count), desc(impressions_count), Ad.id.desc())

    return list(db_session.execute(stmt.limit(limit)).scalars().all())
