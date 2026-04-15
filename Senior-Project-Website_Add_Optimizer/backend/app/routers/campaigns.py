"""Campaign management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Campaign, User
from app.schemas import CampaignCreate, CampaignRead, CampaignUpdate

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignRead])
async def list_campaigns(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CampaignRead]:
    """Return all campaigns ordered by newest first."""
    result = db.execute(select(Campaign).order_by(Campaign.id.desc()))
    return list(result.scalars().all())


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignRead:
    """Create a new campaign record."""
    campaign = Campaign(**payload.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignRead)
async def get_campaign(
    campaign_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignRead:
    """Fetch a campaign by id."""
    result = db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


@router.put("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignRead:
    """Update an existing campaign by id."""
    result = db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(campaign, key, value)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a campaign by id."""
    result = db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    db.delete(campaign)
    db.commit()
