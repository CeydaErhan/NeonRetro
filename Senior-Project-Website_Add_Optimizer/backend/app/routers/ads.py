"""Ad management routes."""

from collections import defaultdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Ad, Campaign, Event, Impression, User, VisitorSession
from app.routers.recommendations import _derive_session_ml_features, _load_model_metadata, _segment_label
from app.schemas import AdCreate, AdPlacementRead, AdRead, AdUpdate, ImpressionClickPayload
from ml.calibration import calibrate_business_segment
from ml.scoring import CATEGORY_SLUGS, MODEL_PATH, score_session

router = APIRouter(prefix="/ads", tags=["ads"])
HOME_CATEGORY_OVERRIDE_THRESHOLD = 0.5


@router.get("", response_model=list[AdRead])
async def list_ads(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[AdRead]:
    """Return all ads ordered by newest first."""
    result = db.execute(select(Ad).order_by(Ad.id.desc()))
    return list(result.scalars().all())


def _target_priority_case(target_column, prioritized_targets: list[str]):
    """Build a stable target priority expression for placement ordering."""
    whens = [(target_column == target, index) for index, target in enumerate(prioritized_targets)]
    return case(*whens, else_=len(prioritized_targets))


def _resolve_prioritized_targets(
    normalized_page: str,
    dominant_category: str | None = None,
    dominant_category_ratio: float = 0.0,
) -> list[str]:
    """Return ordered placement targets with a strong-signal category override for the home page."""
    prioritized_targets: list[str] = []

    def append_target(target: str | None) -> None:
        if not target:
            return
        if target not in prioritized_targets:
            prioritized_targets.append(target)

    if (
        normalized_page == "home"
        and dominant_category
        and dominant_category != normalized_page
        and dominant_category_ratio >= HOME_CATEGORY_OVERRIDE_THRESHOLD
    ):
        append_target(dominant_category)
        append_target(normalized_page)
    else:
        append_target(normalized_page)
    if dominant_category and dominant_category != normalized_page:
        append_target(dominant_category)
    append_target("all")

    return prioritized_targets


def _infer_dominant_category_signal(features: dict[str, float]) -> tuple[str | None, float]:
    """Return the dominant category plus its ratio when session behavior shows a preference."""
    best_category = None
    best_ratio = 0.0
    for category_slug in CATEGORY_SLUGS:
        feature_key = category_slug.replace("-", "_") + "_ratio"
        ratio = float(features.get(feature_key) or 0.0)
        if ratio > best_ratio:
            best_ratio = ratio
            best_category = category_slug

    if best_category and best_ratio > 0:
        return best_category, best_ratio
    return None, 0.0


def _derive_category_override_signal(events: list[Event]) -> tuple[str | None, float]:
    """Return a stronger category-intent signal for home banner overrides.

    This is more responsive than raw ML category ratios because it gives extra
    weight to deeper shopping actions like open-product, attribute selection,
    and add-to-cart.
    """
    weighted_scores: dict[str, float] = defaultdict(float)

    for event in events:
        metadata = event.metadata_json or {}
        category = metadata.get("category")
        if not isinstance(category, str) or category not in CATEGORY_SLUGS:
            continue

        weight = 0.0
        if event.type in {"page_view", "pageview"}:
            weight = 1.0
        elif event.type == "product_view":
            weight = 1.5
        elif event.type == "click":
            if event.element == "open-product":
                weight = 1.5
            elif event.element == "select-attribute":
                weight = 2.5
            elif event.element == "add-to-cart":
                weight = 4.0
            else:
                weight = 1.25

        if weight > 0:
            weighted_scores[category] += weight

    total_score = sum(weighted_scores.values())
    if total_score <= 0:
        return None, 0.0

    best_category, best_score = max(weighted_scores.items(), key=lambda item: item[1])
    return best_category, float(best_score / total_score)


def _fallback_placement_statement(
    normalized_page: str,
    dominant_category: str | None = None,
    dominant_category_ratio: float = 0.0,
):
    """Build the existing least-impression storefront placement query."""
    today = date.today()
    prioritized_targets = _resolve_prioritized_targets(normalized_page, dominant_category, dominant_category_ratio)
    campaign_priority = _target_priority_case(Campaign.target_page, prioritized_targets)
    ad_priority = _target_priority_case(Ad.target_page, prioritized_targets)
    return (
        select(Ad, Campaign, func.count(Impression.id).label("impression_count"))
        .join(Campaign, Campaign.id == Ad.campaign_id)
        .join(Impression, Impression.ad_id == Ad.id, isouter=True)
        .where(Campaign.status == "active")
        .where(Campaign.start_date <= today)
        .where(Campaign.end_date >= today)
        .where(Campaign.target_page.in_(prioritized_targets))
        .where(Ad.target_page.in_(prioritized_targets))
        .group_by(Ad.id, Campaign.id)
        .order_by(campaign_priority.asc(), ad_priority.asc(), func.count(Impression.id).asc(), Campaign.id.desc(), Ad.id.desc())
    )


def _ml_placement_statement(
    normalized_page: str,
    segment: int,
    dominant_category: str | None = None,
    dominant_category_ratio: float = 0.0,
):
    """Build a page-eligible ad query ordered by the KMeans segment strategy."""
    today = date.today()
    prioritized_targets = _resolve_prioritized_targets(normalized_page, dominant_category, dominant_category_ratio)
    campaign_priority = _target_priority_case(Campaign.target_page, prioritized_targets)
    ad_priority = _target_priority_case(Ad.target_page, prioritized_targets)
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
        .where(Campaign.target_page.in_(prioritized_targets))
        .where(Ad.target_page.in_(prioritized_targets))
        .group_by(Ad.id, Campaign.id)
    )

    if segment == 0:
        return stmt.order_by(campaign_priority.asc(), ad_priority.asc(), impressions_count.asc(), Campaign.id.desc(), Ad.id.desc())
    if segment == 1:
        return stmt.order_by(campaign_priority.asc(), ad_priority.asc(), desc(impressions_count), Campaign.id.desc(), Ad.id.desc())
    return stmt.order_by(campaign_priority.asc(), ad_priority.asc(), desc(ctr_value), desc(clicks_count), desc(impressions_count), Ad.id.desc())


def _placement_ranking_strategy(segment: int) -> str:
    """Return the page-placement SDD strategy used for a segment."""
    if segment == 0:
        return "least_exposed_ads"
    if segment == 1:
        return "impression_popularity"
    return "ctr_performance"


def _count_candidates(db: Session, stmt) -> int:
    """Count eligible ad candidates for a grouped placement query."""
    return int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)


def _decision_reason(segment_label: str | None, ranking_strategy: str | None) -> str | None:
    """Build a concise explanation of the ranking rule used."""
    if segment_label and ranking_strategy:
        return f"Segment {segment_label} uses {ranking_strategy} ranking for eligible active ads."
    if ranking_strategy:
        return f"Fallback placement uses {ranking_strategy} ranking for eligible active ads."
    return None


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
    dominant_category: str | None = None,
    segment: int | None = None,
    segment_label: str | None = None,
    kmeans_segment: int | None = None,
    kmeans_segment_label: str | None = None,
    calibration_applied: bool | None = None,
    calibration_reason: str | None = None,
    ranking_strategy: str | None = None,
    model_version: str | None = None,
    explanation: str | None = None,
    features_used: dict | None = None,
    decision_reason: str | None = None,
    fallback_reason: str | None = None,
    candidate_count: int | None = None,
) -> AdPlacementRead:
    """Build the public storefront ad placement response."""
    return AdPlacementRead(
        ad_id=ad.id,
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        selected_target_page=ad.target_page,
        title=ad.title,
        content=ad.content,
        image_url=ad.image_url,
        placement_page=normalized_page,
        dominant_category=dominant_category,
        impression_id=impression_id,
        segment=segment,
        segment_label=segment_label,
        kmeans_segment=kmeans_segment,
        kmeans_segment_label=kmeans_segment_label,
        calibration_applied=calibration_applied,
        calibration_reason=calibration_reason,
        ranking_strategy=ranking_strategy,
        model_version=model_version,
        explanation=explanation,
        features_used=features_used,
        decision_reason=decision_reason,
        fallback_reason=fallback_reason,
        candidate_count=candidate_count,
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
                kmeans_segment = score_session(**features)
                calibration = calibrate_business_segment(kmeans_segment, **features)
                segment = int(calibration["final_segment"])
                dominant_category, dominant_category_ratio = _derive_category_override_signal(events)
                if dominant_category is None:
                    dominant_category, dominant_category_ratio = _infer_dominant_category_signal(features)
                ml_stmt = _ml_placement_statement(
                    normalized_page,
                    segment,
                    dominant_category,
                    dominant_category_ratio,
                )
                candidate_count = _count_candidates(db, ml_stmt)
                ml_placement = db.execute(ml_stmt).first()
                if ml_placement is not None:
                    ad, campaign, _ = ml_placement
                    model_metadata = _load_model_metadata() or {}
                    model_version = model_metadata.get("model_version")
                    segment_label = _segment_label(segment)
                    kmeans_segment_label = _segment_label(kmeans_segment)
                    ranking_strategy = _placement_ranking_strategy(segment)
                    impression_id = _create_impression(db, ad, session)
                    return _build_placement_response(
                        ad=ad,
                        campaign=campaign,
                        normalized_page=normalized_page,
                        impression_id=impression_id,
                        dominant_category=dominant_category,
                        segment=segment,
                        segment_label=segment_label,
                        kmeans_segment=kmeans_segment,
                        kmeans_segment_label=kmeans_segment_label,
                        calibration_applied=bool(calibration["calibration_applied"]),
                        calibration_reason=(
                            str(calibration["calibration_reason"])
                            if calibration["calibration_reason"] is not None
                            else None
                        ),
                        ranking_strategy=ranking_strategy,
                        model_version=str(model_version) if model_version is not None else None,
                        explanation="ml:kmeans_segment_placement",
                        features_used=features,
                        decision_reason=_decision_reason(segment_label, ranking_strategy),
                        candidate_count=candidate_count,
                    )
                fallback_explanation = "fallback:no_ml_ad"
            except Exception:
                fallback_explanation = "fallback:scoring_failed"

    dominant_category = None
    fallback_stmt = _fallback_placement_statement(normalized_page, dominant_category)
    candidate_count = _count_candidates(db, fallback_stmt)
    placement = db.execute(fallback_stmt).first()
    if placement is None:
        return None

    ad, campaign, _ = placement
    impression_id = _create_impression(db, ad, session)
    return _build_placement_response(
        ad=ad,
        campaign=campaign,
        normalized_page=normalized_page,
        impression_id=impression_id,
        dominant_category=dominant_category,
        explanation=fallback_explanation,
        ranking_strategy="least_exposed_ads",
        decision_reason=_decision_reason(None, "least_exposed_ads"),
        fallback_reason=fallback_explanation.removeprefix("fallback:") if fallback_explanation else None,
        candidate_count=candidate_count,
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
