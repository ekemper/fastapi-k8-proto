from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.campaign import CampaignService


def get_campaign_service() -> CampaignService:
    """
    Dependency to provide CampaignService instance.
    
    Returns:
        CampaignService: A new instance of the campaign service
    """
    return CampaignService()


def get_campaign_service_with_db(db: Session = Depends(get_db)) -> CampaignService:
    """
    Dependency to provide CampaignService instance with database session.
    This is an alternative pattern if the service needs the DB session at initialization.
    
    Args:
        db: Database session from dependency injection
        
    Returns:
        CampaignService: A new instance of the campaign service
    """
    # Note: Current CampaignService doesn't take db in __init__
    # This is here for future use if needed
    return CampaignService() 