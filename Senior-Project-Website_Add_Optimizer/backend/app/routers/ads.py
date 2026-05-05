"""Ad management routes."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Ad, Campaign, Impression, User, VisitorSession
from app.schemas import AdCreate, AdPlacementRead, AdRead, AdUpdate, ImpressionClickPayload

router = APIRouter(prefix="/ads", tags=["ads"])


@router.get("", response_model=list[AdRead])
async def list_ads(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[AdRead]:
    """Return all ads ordered by newest first."""
    result = db.execute(select(Ad).order_by(Ad.id.desc()))
    return list(result.scalars().all())


@router.get("/placement", response_model=AdPlacementRead | None)
async def get_ad_placement(
    page: str,
    session_id: int | None = None,
    db: Session = Depends(get_db),
) -> AdPlacementRead | None:
    """Return one active ad for a storefront placement and optionally record an impression."""
    normalized_page = page.strip().lower()
    today = date.today()

    stmt = (
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
    placement = db.execute(stmt).first()
    if placement is None:
        return None

    ad, campaign, _ = placement
    impression_id = None

    if session_id is not None:
        session = db.execute(select(VisitorSession).where(VisitorSession.id == session_id)).scalar_one_or_none()
        if session is not None:
            impression = Impression(ad_id=ad.id, session_id=session.id, clicked=False)
            db.add(impression)
            db.commit()
            db.refresh(impression)
            impression_id = impression.id

    return AdPlacementRead(
        ad_id=ad.id,
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        title=ad.title,
        content=ad.content,
        image_url=ad.image_url,
        placement_page=normalized_page,
        impression_id=impression_id,
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
