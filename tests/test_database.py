import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.models.job import Job, JobStatus
from app.main import app
from fastapi.testclient import TestClient

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def test_create_job():
    db = TestingSessionLocal()
    
    # Create a test job
    job = Job(
        name="Test Job",
        description="Test Description",
        status=JobStatus.PENDING,
        task_id="test-task-123"
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Verify job was created
    assert job.id is not None
    assert job.name == "Test Job"
    assert job.status == JobStatus.PENDING
    
    # Clean up
    db.delete(job)
    db.commit()
    db.close()

def test_job_status_enum():
    assert JobStatus.PENDING.value == "pending"
    assert JobStatus.PROCESSING.value == "processing"
    assert JobStatus.COMPLETED.value == "completed"
    assert JobStatus.FAILED.value == "failed"
    assert JobStatus.CANCELLED.value == "cancelled" 