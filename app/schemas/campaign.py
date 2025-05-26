from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.campaign_status import CampaignStatus


class CampaignBase(BaseModel):
    """Base campaign schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")
    organization_id: Optional[str] = Field(None, max_length=36, description="Organization ID")
    fileName: str = Field(..., min_length=1, max_length=255, description="File name for the campaign")
    totalRecords: int = Field(..., ge=0, description="Total number of records in the campaign")
    url: str = Field(..., min_length=1, description="URL for the campaign")


class CampaignCreate(CampaignBase):
    """Schema for creating a new campaign."""
    pass


class CampaignUpdate(BaseModel):
    """Schema for updating an existing campaign."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")
    status: Optional[CampaignStatus] = Field(None, description="Campaign status")
    status_message: Optional[str] = Field(None, description="Status message")
    status_error: Optional[str] = Field(None, description="Status error message")
    organization_id: Optional[str] = Field(None, max_length=36, description="Organization ID")
    fileName: Optional[str] = Field(None, min_length=1, max_length=255, description="File name")
    totalRecords: Optional[int] = Field(None, ge=0, description="Total number of records")
    url: Optional[str] = Field(None, min_length=1, description="Campaign URL")
    instantly_campaign_id: Optional[str] = Field(None, max_length=64, description="Instantly campaign ID")


class CampaignInDB(CampaignBase):
    """Schema representing campaign as stored in database."""
    id: str = Field(..., description="Campaign ID")
    status: CampaignStatus = Field(..., description="Campaign status")
    status_message: Optional[str] = Field(None, description="Status message")
    status_error: Optional[str] = Field(None, description="Status error message")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    failed_at: Optional[datetime] = Field(None, description="Failure timestamp")
    instantly_campaign_id: Optional[str] = Field(None, max_length=64, description="Instantly campaign ID")

    class Config:
        from_attributes = True


class CampaignResponse(CampaignInDB):
    """Schema for campaign API responses."""
    valid_transitions: List[CampaignStatus] = Field(..., description="Valid status transitions from current state")

    @classmethod
    def from_campaign(cls, campaign):
        """Create response schema from campaign model."""
        return cls(
            id=campaign.id,
            name=campaign.name,
            description=campaign.description,
            organization_id=campaign.organization_id,
            fileName=campaign.fileName,
            totalRecords=campaign.totalRecords,
            url=campaign.url,
            status=campaign.status,
            status_message=campaign.status_message,
            status_error=campaign.status_error,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
            completed_at=campaign.completed_at,
            failed_at=campaign.failed_at,
            instantly_campaign_id=campaign.instantly_campaign_id,
            valid_transitions=campaign.get_valid_transitions()
        )


class CampaignStart(BaseModel):
    """Schema for starting a campaign."""
    status_message: Optional[str] = Field(None, description="Optional message when starting campaign")


class CampaignStatusUpdate(BaseModel):
    """Schema for updating campaign status."""
    status: CampaignStatus = Field(..., description="New campaign status")
    status_message: Optional[str] = Field(None, description="Optional status message")
    status_error: Optional[str] = Field(None, description="Optional error message")
    instantly_campaign_id: Optional[str] = Field(None, max_length=64, description="Instantly campaign ID") 