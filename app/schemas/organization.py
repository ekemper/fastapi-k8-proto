from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    """Base organization schema with common fields."""
    name: str = Field(..., min_length=3, max_length=255, description="Organization name")
    description: str = Field(..., min_length=1, description="Organization description")


class OrganizationCreate(OrganizationBase):
    """Schema for creating a new organization."""
    pass


class OrganizationUpdate(BaseModel):
    """Schema for updating an existing organization."""
    name: Optional[str] = Field(None, min_length=3, max_length=255, description="Organization name")
    description: Optional[str] = Field(None, min_length=1, description="Organization description")


class OrganizationInDB(OrganizationBase):
    """Schema representing organization as stored in database."""
    id: str = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class OrganizationResponse(OrganizationInDB):
    """Schema for organization API responses."""
    pass 