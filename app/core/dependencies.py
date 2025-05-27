from typing import Generator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.campaign import CampaignService
from app.services.auth_service import AuthService
from app.models.user import User


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


# Auth dependencies
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user."""
    auth_service = AuthService()
    return auth_service.get_current_user(credentials.credentials, db)

def get_current_user_from_middleware(request: Request) -> User:
    """Dependency to get current user from middleware state."""
    if not hasattr(request.state, 'current_user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    return request.state.current_user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to get current active user (can be extended with user status checks)."""
    return current_user 