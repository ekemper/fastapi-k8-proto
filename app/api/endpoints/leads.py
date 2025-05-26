from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse
from app.services.lead import LeadService

router = APIRouter()

@router.get("/", response_model=List[LeadResponse])
async def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    db: Session = Depends(get_db)
):
    """List all leads with optional pagination and campaign filtering"""
    lead_service = LeadService()
    leads_data = await lead_service.get_leads(db, campaign_id=campaign_id)
    leads = []
    for lead_dict in leads_data:
        lead = db.query(Lead).filter(Lead.id == lead_dict['id']).first()
        if lead:
            leads.append(LeadResponse(**lead.to_dict()))
    return leads[skip:skip + limit]

@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_in: LeadCreate,
    db: Session = Depends(get_db)
):
    """Create a new lead"""
    lead_service = LeadService()
    lead_dict = await lead_service.create_lead(lead_in, db)
    lead = db.query(Lead).filter(Lead.id == lead_dict['id']).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lead created but could not be retrieved"
        )
    return LeadResponse(**lead.to_dict())

@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific lead by ID"""
    lead_service = LeadService()
    lead_dict = await lead_service.get_lead(lead_id, db)
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found"
        )
    return LeadResponse(**lead.to_dict())

@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: str,
    lead_update: LeadUpdate,
    db: Session = Depends(get_db)
):
    """Update a specific lead by ID"""
    lead_service = LeadService()
    lead_dict = await lead_service.update_lead(lead_id, lead_update, db)
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found"
        )
    return LeadResponse(**lead.to_dict()) 