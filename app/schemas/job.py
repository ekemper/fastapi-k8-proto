from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.job import JobStatus

class JobBase(BaseModel):
    name: str
    description: Optional[str] = None

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    result: Optional[str] = None
    error: Optional[str] = None

class JobInDB(JobBase):
    id: int
    task_id: str
    status: JobStatus
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobResponse(JobInDB):
    pass 