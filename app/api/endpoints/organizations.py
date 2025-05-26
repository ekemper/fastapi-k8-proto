from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.organization import Organization
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate
)
from app.services.organization import OrganizationService

router = APIRouter()

@router.get("/", response_model=List[OrganizationResponse])
async def list_organizations(
    db: Session = Depends(get_db)
):
    """Get all organizations"""
    organization_service = OrganizationService()
    organizations_data = await organization_service.get_organizations(db)
    
    # Convert to response models
    organizations = []
    for org_dict in organizations_data:
        org = db.query(Organization).filter(Organization.id == org_dict['id']).first()
        if org:
            organizations.append(OrganizationResponse.model_validate(org))
    
    return organizations

@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_in: OrganizationCreate,
    db: Session = Depends(get_db)
):
    """Create a new organization"""
    organization_service = OrganizationService()
    org_dict = await organization_service.create_organization(organization_in, db)
    
    # Get the organization object to create proper response
    organization = db.query(Organization).filter(Organization.id == org_dict['id']).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Organization created but could not be retrieved"
        )
    
    return OrganizationResponse.model_validate(organization)

@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific organization by ID"""
    organization_service = OrganizationService()
    org_dict = await organization_service.get_organization(org_id, db)
    
    if not org_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {org_id} not found"
        )
    
    # Get the organization object to create proper response
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    return OrganizationResponse.model_validate(organization)

@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    organization_update: OrganizationUpdate,
    db: Session = Depends(get_db)
):
    """Update organization properties"""
    organization_service = OrganizationService()
    org_dict = await organization_service.update_organization(org_id, organization_update, db)
    
    if not org_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {org_id} not found"
        )
    
    # Get the organization object to create proper response
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    return OrganizationResponse.model_validate(organization) 