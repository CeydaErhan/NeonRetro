"""Ad management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Ad, Campaign, User
from app.schemas import AdCreate, AdRead, AdUpdate

router = APIRouter(prefix="/ads", tags=["ads"])


@router.get("", response_model=list[AdRead])
async def list_ads(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[AdRead]:
    """Return all ads ordered by newest first."""
    result = db.execute(select(Ad).order_by(Ad.id.desc()))
    return list(result.scalars().all())


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
