from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campaign import Campaign
from app.schemas.campaign import (
    CampaignCreate, 
    CampaignResponse, 
    CampaignUpdate, 
    CampaignStart
)
from app.services.campaign import CampaignService

router = APIRouter()

@router.get("/", response_model=List[CampaignResponse])
async def list_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    db: Session = Depends(get_db)
):
    """List all campaigns with optional pagination and organization filtering"""
    campaign_service = CampaignService()
    campaigns_data = await campaign_service.get_campaigns(db, organization_id=organization_id)
    
    # Convert to response models
    campaigns = []
    for campaign_dict in campaigns_data:
        # Get the campaign object to create proper response
        campaign = db.query(Campaign).filter(Campaign.id == campaign_dict['id']).first()
        if campaign:
            campaigns.append(CampaignResponse.from_campaign(campaign))
    
    # Apply pagination
    return campaigns[skip:skip + limit]

@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_in: CampaignCreate,
    db: Session = Depends(get_db)
):
    """Create a new campaign"""
    campaign_service = CampaignService()
    campaign_dict = await campaign_service.create_campaign(campaign_in, db)
    
    # Get the campaign object to create proper response
    campaign = db.query(Campaign).filter(Campaign.id == campaign_dict['id']).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Campaign created but could not be retrieved"
        )
    
    return CampaignResponse.from_campaign(campaign)

@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific campaign by ID"""
    campaign_service = CampaignService()
    campaign_dict = await campaign_service.get_campaign(campaign_id, db)
    
    # Get the campaign object to create proper response
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    return CampaignResponse.from_campaign(campaign)

@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    campaign_update: CampaignUpdate,
    db: Session = Depends(get_db)
):
    """Update campaign properties"""
    campaign_service = CampaignService()
    campaign_dict = await campaign_service.update_campaign(campaign_id, campaign_update, db)
    
    # Get the campaign object to create proper response
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    return CampaignResponse.from_campaign(campaign)

@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(
    campaign_id: str,
    start_data: CampaignStart = CampaignStart(),
    db: Session = Depends(get_db)
):
    """Start campaign process"""
    campaign_service = CampaignService()
    campaign_dict = await campaign_service.start_campaign(campaign_id, start_data, db)
    
    # Get the campaign object to create proper response
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    return CampaignResponse.from_campaign(campaign)

@router.get("/{campaign_id}/details")
async def get_campaign_details(
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """Get campaign details including lead stats and Instantly analytics"""
    campaign_service = CampaignService()
    
    # Get campaign
    campaign_dict = await campaign_service.get_campaign(campaign_id, db)
    
    # Get lead stats
    lead_stats = await campaign_service.get_campaign_lead_stats(campaign_id, db)
    
    # Get Instantly analytics
    instantly_analytics = await campaign_service.get_campaign_instantly_analytics(campaign_id, db)
    
    return {
        "status": "success",
        "data": {
            "campaign": campaign_dict,
            "lead_stats": lead_stats,
            "instantly_analytics": instantly_analytics
        }
    }

@router.post("/{campaign_id}/cleanup")
async def cleanup_campaign_jobs(
    campaign_id: str,
    cleanup_data: Dict[str, int],
    db: Session = Depends(get_db)
):
    """Clean up old jobs for a campaign"""
    if "days" not in cleanup_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days parameter is required"
        )
    
    days = cleanup_data["days"]
    if days <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be a positive integer"
        )
    
    campaign_service = CampaignService()
    result = await campaign_service.cleanup_campaign_jobs(campaign_id, days, db)
    
    return {
        "status": "success",
        "message": result["message"],
        "jobs_deleted": result.get("jobs_deleted", 0)
    }

@router.get("/{campaign_id}/results")
async def get_campaign_results(
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """Get campaign results from completed jobs"""
    from app.models.job import Job, JobStatus
    
    # Get campaign
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    # Get completed jobs
    completed_jobs = (
        db.query(Job)
        .filter(
            Job.campaign_id == campaign_id,
            Job.status == JobStatus.COMPLETED
        )
        .all()
    )
    
    if not completed_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed jobs found for this campaign"
        )
    
    # Collect results from completed jobs
    results = {}
    for job in completed_jobs:
        # Note: Job result validation would be implemented in the Job model
        # For now, we'll include the results as-is
        results[job.name] = getattr(job, 'result', None)
    
    return {
        "status": "success",
        "data": {
            "campaign": campaign.to_dict(),
            "results": results
        }
    } 