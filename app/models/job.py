from sqlalchemy import Column, Integer, String, DateTime, Enum, Text
from sqlalchemy.sql import func
import enum

from app.core.database import Base

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    result = Column(Text)
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True)) 