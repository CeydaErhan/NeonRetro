"""Ad management routes."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Ad, Campaign, Event, Impression, User, VisitorSession
from app.routers.recommendations import _derive_session_ml_features, _load_model_metadata, _segment_label
from app.schemas import AdCreate, AdPlacementRead, AdRead, AdUpdate, ImpressionClickPayload
from ml.scoring import MODEL_PATH, score_session

router = APIRouter(prefix="/ads", tags=["ads"])


@router.get("", response_model=list[AdRead])
async def list_ads(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[AdRead]:
    """Return all ads ordered by newest first."""
    result = db.execute(select(Ad).order_by(Ad.id.desc()))
    return list(result.scalars().all())


def _fallback_placement_statement(normalized_page: str):
    """Build the existing least-impression storefront placement query."""
    today = date.today()
    return (
        select(Ad, Campaign, func.count(Impression.id).label("impression_count"))
        .join(Campaign, Campaign.id == Ad.campaign_id)
        .join(Impression, Impression.ad_id == Ad.id, isouter=True)
        .where(Campaign.status == "active")
        .where(Campaign.start_date <= today)
        .where(Campaign.end_date >= today)
        .where(Campaign.target_page.in_([normalized_page, "all"]))
        .where(Ad.target_page.in_([normalized_page, "all"]))
        .group_by(Ad.id, Campaign.id)
        .order_by(func.count(Impression.id).asc(), Campaign.id.desc(), Ad.id.desc())
    )


def _ml_placement_statement(normalized_page: str, segment: int):
    """Build a page-eligible ad query ordered by the KMeans segment strategy."""
    today = date.today()
    impressions_count = func.count(Impression.id)
    clicks_count = func.sum(case((Impression.clicked.is_(True), 1), else_=0))
    ctr_value = func.coalesce(
        func.sum(case((Impression.clicked.is_(True), 1.0), else_=0.0)) / func.nullif(impressions_count, 0),
        0.0,
    )

    stmt = (
        select(Ad, Campaign, impressions_count.label("impression_count"))
        .join(Campaign, Campaign.id == Ad.campaign_id)
        .join(Impression, Impression.ad_id == Ad.id, isouter=True)
        .where(Campaign.status == "active")
        .where(Campaign.start_date <= today)
        .where(Campaign.end_date >= today)
        .where(Campaign.target_page.in_([normalized_page, "all"]))
        .where(Ad.target_page.in_([normalized_page, "all"]))
        .group_by(Ad.id, Campaign.id)
    )

    if segment == 0:
        return stmt.order_by(impressions_count.asc(), Campaign.id.desc(), Ad.id.desc())
    if segment == 1:
        return stmt.order_by(desc(impressions_count), Campaign.id.desc(), Ad.id.desc())
    return stmt.order_by(desc(ctr_value), desc(clicks_count), desc(impressions_count), Ad.id.desc())


def _placement_ranking_strategy(segment: int) -> str:
    """Return the page-placement SDD strategy used for a segment."""
    if segment == 0:
        return "least_exposed_ads"
    if segment == 1:
        return "impression_popularity"
    return "ctr_performance"


def _create_impression(db: Session, ad: Ad, session: VisitorSession | None) -> int | None:
    """Record the selected placement when a valid visitor session is available."""
    if session is None:
        return None
    impression = Impression(ad_id=ad.id, session_id=session.id, clicked=False)
    db.add(impression)
    db.commit()
    db.refresh(impression)
    return impression.id


def _build_placement_response(
    *,
    ad: Ad,
    campaign: Campaign,
    normalized_page: str,
    impression_id: int | None,
    segment: int | None = None,
    segment_label: str | None = None,
    ranking_strategy: str | None = None,
    model_version: str | None = None,
    explanation: str | None = None,
) -> AdPlacementRead:
    """Build the public storefront ad placement response."""
    return AdPlacementRead(
        ad_id=ad.id,
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        title=ad.title,
        content=ad.content,
        image_url=ad.image_url,
        placement_page=normalized_page,
        impression_id=impression_id,
        segment=segment,
        segment_label=segment_label,
        ranking_strategy=ranking_strategy,
        model_version=model_version,
        explanation=explanation,
    )


@router.get("/placement", response_model=AdPlacementRead | None)
async def get_ad_placement(
    page: str,
    session_id: int | None = None,
    db: Session = Depends(get_db),
) -> AdPlacementRead | None:
    """Return one active ad for a storefront placement and optionally record an impression."""
    normalized_page = page.strip().lower()

    session = None
    fallback_explanation = "fallback:no_session_id" if session_id is None else None
    if session_id is not None:
        session = db.execute(select(VisitorSession).where(VisitorSession.id == session_id)).scalar_one_or_none()
        if session is None:
            fallback_explanation = "fallback:session_not_found"
        elif not MODEL_PATH.exists():
            fallback_explanation = "fallback:model_missing"
        else:
            try:
                events = list(
                    db.execute(
                        select(Event)
                        .where(Event.session_id == session_id)
                        .order_by(Event.timestamp.asc(), Event.id.asc())
                    )
                    .scalars()
                    .all()
                )
                features = _derive_session_ml_features(session, events)
                segment = score_session(**features)
                ml_placement = db.execute(_ml_placement_statement(normalized_page, segment)).first()
                if ml_placement is not None:
                    ad, campaign, _ = ml_placement
                    model_metadata = _load_model_metadata() or {}
                    model_version = model_metadata.get("model_version")
                    impression_id = _create_impression(db, ad, session)
                    return _build_placement_response(
                        ad=ad,
                        campaign=campaign,
                        normalized_page=normalized_page,
                        impression_id=impression_id,
                        segment=segment,
                        segment_label=_segment_label(segment),
                        ranking_strategy=_placement_ranking_strategy(segment),
                        model_version=str(model_version) if model_version is not None else None,
                        explanation="ml:kmeans_segment_placement",
                    )
                fallback_explanation = "fallback:no_ml_ad"
            except Exception:
                fallback_explanation = "fallback:scoring_failed"

    placement = db.execute(_fallback_placement_statement(normalized_page)).first()
    if placement is None:
        return None

    ad, campaign, _ = placement
    impression_id = _create_impression(db, ad, session)
    return _build_placement_response(
        ad=ad,
        campaign=campaign,
        normalized_page=normalized_page,
        impression_id=impression_id,
        explanation=fallback_explanation,
    )


@router.post("", response_model=AdRead, status_code=status.HTTP_201_CREATED)
async def create_ad(payload: AdCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AdRead:
    """Create a new ad record."""
    campaign_result = db.execute(select(Campaign).where(Campaign.id == payload.campaign_id))
    campaign = campaign_result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    ad = Ad(**payload.model_dump())
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


@router.post("/impressions/{impression_id}/click")
async def click_impression(
    impression_id: int,
    payload: ImpressionClickPayload,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Mark a previously created ad impression as clicked."""
    impression = db.execute(select(Impression).where(Impression.id == impression_id)).scalar_one_or_none()
    if impression is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Impression not found")

    if payload.session_id is not None and impression.session_id != payload.session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session does not match impression")

    impression.clicked = True
    impression.click_time = datetime.utcnow()
    db.commit()

    return {
        "impression_id": impression.id,
        "ad_id": impression.ad_id,
        "clicked": impression.clicked,
    }


@router.get("/{ad_id}", response_model=AdRead)
async def get_ad(ad_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AdRead:
    """Fetch an ad by id."""
    result = db.execute(select(Ad).where(Ad.id == ad_id))
    ad = result.scalar_one_or_none()
    if ad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found")
    return ad


@router.put("/{ad_id}", response_model=AdRead)
async def update_ad(
    ad_id: int,
    payload: AdUpdate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdRead:
    """Update an existing ad by id."""
    result = db.execute(select(Ad).where(Ad.id == ad_id))
    ad = result.scalar_one_or_none()
    if ad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found")

    updates = payload.model_dump(exclude_unset=True)
    if "campaign_id" in updates:
        campaign_result = db.execute(select(Campaign).where(Campaign.id == updates["campaign_id"]))
        campaign = campaign_result.scalar_one_or_none()
        if campaign is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    for key, value in updates.items():
        setattr(ad, key, value)
    db.commit()
    db.refresh(ad)
    return ad


@router.delete("/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ad(ad_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    """Delete an ad by id."""
    result = db.execute(select(Ad).where(Ad.id == ad_id))
    ad = result.scalar_one_or_none()
    if ad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found")
    db.delete(ad)
    db.commit()
