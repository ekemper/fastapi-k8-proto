import pytest
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.models.job import Job, JobStatus, JobType
from app.main import app
from fastapi.testclient import TestClient

def test_create_job(db_session):
    # Create a test job
    job = Job(
        name="Test Job",
        description="Test Description",
        job_type=JobType.GENERAL,
        status=JobStatus.PENDING,
        task_id="test-task-123"
    )
    
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    # Verify job was created
    assert job.id is not None
    assert job.name == "Test Job"
    assert job.status == JobStatus.PENDING
    
    # Clean up
    db_session.delete(job)
    db_session.commit()

def test_job_status_enum():
    assert JobStatus.PENDING.value == "pending"
    assert JobStatus.PROCESSING.value == "processing"
    assert JobStatus.COMPLETED.value == "completed"
    assert JobStatus.FAILED.value == "failed"
    assert JobStatus.CANCELLED.value == "cancelled" 