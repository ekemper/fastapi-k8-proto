# Phase 3: Redis and Celery Setup

## Overview
This phase integrates Redis as a message broker and Celery for distributed task processing, creating the foundation for scalable worker processes.

## Prerequisites
- Phase 1 and Phase 2 completed successfully
- Redis installed locally or accessible via Docker
- PostgreSQL running from Phase 2
- Virtual environment activated

## Step 3.1: Update Requirements

### AI Agent Instructions:
**Task**: Add Redis and Celery dependencies to the requirements files.

**Action**: Update `requirements/base.txt` by appending the following lines:
```
celery[redis]==5.3.4
redis==5.0.1
flower==2.0.1
```

**Command to execute**:
```bash
pip install -r requirements/dev.txt
```

**Expected outcome**: All Redis and Celery packages installed successfully.

## Step 3.2: Celery Configuration

### AI Agent Instructions:
**Task**: Update the configuration file to include Redis and Celery settings.

**Action**: Modify `app/core/config.py` to add Redis and Celery configuration. Replace the entire file with:
```python
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI K8s Worker Prototype"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "fastapi_k8_proto"
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_connection(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        postgres_server = values.data.get("POSTGRES_SERVER")
        postgres_user = values.data.get("POSTGRES_USER")
        postgres_password = values.data.get("POSTGRES_PASSWORD")
        postgres_db = values.data.get("POSTGRES_DB")
        return f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}/{postgres_db}"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = ""

    @field_validator("REDIS_URL", mode="before")
    def assemble_redis_connection(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        redis_host = values.data.get("REDIS_HOST")
        redis_port = values.data.get("REDIS_PORT")
        redis_db = values.data.get("REDIS_DB")
        return f"redis://{redis_host}:{redis_port}/{redis_db}"

    # Celery
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    @field_validator("CELERY_BROKER_URL", mode="before")
    def set_celery_broker(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        return values.data.get("REDIS_URL", "")

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    def set_celery_backend(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        return values.data.get("REDIS_URL", "")

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
```

**Expected outcome**: Configuration file updated with Redis and Celery settings.

## Step 3.3: Create Celery App

### AI Agent Instructions:
**Task**: Create the Celery application configuration.

**Action 1**: Create the workers directory:
```bash
mkdir -p app/workers
touch app/workers/__init__.py
```

**Action 2**: Create `app/workers/celery_app.py` with the following content:
```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
```

**Action 3**: Start Redis (if not already running):
```bash
# Using Docker
docker run -d \
  --name redis-dev \
  -p 6379:6379 \
  redis:7-alpine
```

**Expected outcome**: Celery app configured and Redis running.

## Step 3.4: Create Worker Tasks

### AI Agent Instructions:
**Task**: Create Celery tasks for job processing.

**Action**: Create `app/workers/tasks.py` with the following content:
```python
import time
import random
from datetime import datetime
from celery import current_task
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.job import Job, JobStatus

@celery_app.task(bind=True, name="process_job")
def process_job(self, job_id: int):
    """
    Simulated long-running task that processes a job
    """
    db: Session = SessionLocal()
    
    try:
        # Update job status to processing
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = JobStatus.PROCESSING
        job.task_id = self.request.id
        db.commit()
        
        # Simulate work with progress updates
        total_steps = 10
        for i in range(total_steps):
            # Update task state
            current_task.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": total_steps,
                    "status": f"Processing step {i + 1}/{total_steps}"
                }
            )
            
            # Simulate work
            time.sleep(random.uniform(1, 3))
            
            # Randomly fail some jobs for testing
            if random.random() < 0.1:  # 10% failure rate
                raise Exception("Random processing error")
        
        # Mark job as completed
        job.status = JobStatus.COMPLETED
        job.result = f"Successfully processed {total_steps} steps"
        job.completed_at = datetime.utcnow()
        db.commit()
        
        return {
            "job_id": job_id,
            "status": "completed",
            "result": job.result
        }
        
    except Exception as e:
        # Mark job as failed
        if job:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        
        raise
    
    finally:
        db.close()

@celery_app.task(name="health_check")
def health_check():
    """Simple task to verify Celery is working"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
```

**Expected outcome**: Worker tasks created for job processing.

## Step 3.5: Update Job Endpoints

### AI Agent Instructions:
**Task**: Implement the job API endpoints with Celery integration.

**Action**: Replace the content of `app/api/endpoints/jobs.py` with:
```python
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.schemas.job import JobCreate, JobResponse, JobUpdate
from app.workers.tasks import process_job

router = APIRouter()

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate,
    db: Session = Depends(get_db)
):
    """Create a new job and queue it for processing"""
    # Create job in database
    job = Job(
        name=job_in.name,
        description=job_in.description,
        status=JobStatus.PENDING
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Queue job for processing
    task = process_job.delay(job.id)
    
    # Update job with task ID
    job.task_id = task.id
    db.commit()
    db.refresh(job)
    
    return job

@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[JobStatus] = None,
    db: Session = Depends(get_db)
):
    """List all jobs with optional status filter"""
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    
    jobs = query.offset(skip).limit(limit).all()
    return jobs

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific job by ID"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    return job

@router.get("/{job_id}/status")
async def get_job_status(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get job status including Celery task progress"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    response = {
        "job_id": job.id,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "completed_at": job.completed_at
    }
    
    # Get Celery task status if available
    if job.task_id and job.status == JobStatus.PROCESSING:
        from app.workers.celery_app import celery_app
        task_result = celery_app.AsyncResult(job.task_id)
        
        if task_result.state == "PROGRESS":
            response["progress"] = task_result.info
        else:
            response["task_state"] = task_result.state
    
    return response

@router.delete("/{job_id}")
async def cancel_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Cancel a pending or processing job"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in {job.status} status"
        )
    
    # Revoke Celery task if it exists
    if job.task_id:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(job.task_id, terminate=True)
    
    # Update job status
    job.status = JobStatus.CANCELLED
    db.commit()
    
    return {"message": f"Job {job_id} cancelled"}
```

**Expected outcome**: Job endpoints implemented with full Celery integration.

## Step 3.6: Test Celery Integration

### AI Agent Instructions:
**Task**: Start all services and test the complete job processing workflow.

**Action 1**: Ensure all services are running:
```bash
# Check Docker containers
docker ps

# Should see postgres-dev and redis-dev running
```

**Action 2**: Start Celery worker in a new terminal:
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info
```

**Action 3**: Start Flower (Celery monitoring) in another terminal:
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start Flower
celery -A app.workers.celery_app flower
```

**Action 4**: Start FastAPI in another terminal:
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start FastAPI
uvicorn app.main:app --reload
```

**Action 5**: Test job creation and processing:
```bash
# Create a job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Job", "description": "Testing Celery integration"}'

# Note the job ID from the response, then check job status (replace 1 with actual ID)
curl http://localhost:8000/api/v1/jobs/1/status

# List all jobs
curl http://localhost:8000/api/v1/jobs

# Get specific job details
curl http://localhost:8000/api/v1/jobs/1
```

**Action 6**: Check Flower UI:
```bash
# Open in browser
open http://localhost:5555
```

**Expected outcome**:
- Job created successfully
- Job status changes from PENDING to PROCESSING to COMPLETED
- Progress updates visible in status endpoint
- Flower shows active tasks and workers

## Step 3.7: Create Integration Tests

### AI Agent Instructions:
**Task**: Create comprehensive tests for the Celery integration.

**Action 1**: Create `tests/test_celery_integration.py`:
```python
import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.workers.tasks import health_check

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
client = TestClient(app)

def test_celery_health_check():
    """Test that Celery is configured correctly"""
    result = health_check.delay()
    assert result.get(timeout=5)["status"] == "healthy"

def test_create_job_endpoint():
    """Test job creation via API"""
    response = client.post(
        "/api/v1/jobs",
        json={"name": "Test Job", "description": "Test description"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Job"
    assert data["status"] == "pending"
    assert "task_id" in data
    return data["id"]

def test_job_status_endpoint():
    """Test job status retrieval"""
    # Create a job
    job_id = test_create_job_endpoint()
    
    # Check status
    response = client.get(f"/api/v1/jobs/{job_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert "status" in data

def test_list_jobs_endpoint():
    """Test listing jobs with filters"""
    # List all jobs
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
    # List with status filter
    response = client.get("/api/v1/jobs?status=pending")
    assert response.status_code == 200

def test_cancel_job_endpoint():
    """Test job cancellation"""
    # Create a job
    job_id = test_create_job_endpoint()
    
    # Cancel it
    response = client.delete(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    assert "cancelled" in response.json()["message"]
```

**Action 2**: Create `tests/test_worker_tasks.py`:
```python
import pytest
from unittest.mock import Mock, patch
from app.workers.tasks import process_job, health_check
from app.models.job import JobStatus

def test_health_check_task():
    """Test the health check task"""
    result = health_check()
    assert result["status"] == "healthy"
    assert "timestamp" in result

@patch('app.workers.tasks.SessionLocal')
def test_process_job_success(mock_session):
    """Test successful job processing"""
    # Mock database session and job
    mock_db = Mock()
    mock_job = Mock()
    mock_job.id = 1
    mock_job.status = JobStatus.PENDING
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job
    mock_session.return_value = mock_db
    
    # Mock the task
    mock_task = Mock()
    mock_task.request.id = "test-task-id"
    
    # Test with mocked sleep to speed up test
    with patch('time.sleep'):
        with patch('random.random', return_value=0.5):  # Ensure no random failure
            result = process_job.apply(args=[1], task_id="test-task-id").get()
    
    assert result["job_id"] == 1
    assert result["status"] == "completed"
    assert mock_job.status == JobStatus.COMPLETED

@patch('app.workers.tasks.SessionLocal')
def test_process_job_not_found(mock_session):
    """Test processing non-existent job"""
    # Mock database session with no job found
    mock_db = Mock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_session.return_value = mock_db
    
    # Test that it raises ValueError
    with pytest.raises(ValueError, match="Job .* not found"):
        process_job.apply(args=[999]).get()
```

**Action 3**: Run all tests:
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

**Expected outcome**: All tests pass successfully.

## Phase 3 Completion Checklist

- [ ] Redis and Celery dependencies added
- [ ] Configuration updated with Redis/Celery settings
- [ ] Celery app created and configured
- [ ] Redis service running
- [ ] Worker tasks implemented
- [ ] Job API endpoints fully implemented
- [ ] Celery worker running successfully
- [ ] Flower monitoring accessible
- [ ] Job creation and processing working end-to-end
- [ ] All integration tests passing

## Troubleshooting

### Common Issues:

1. **Celery worker not starting**:
   - Check Redis is running: `docker ps`
   - Verify Redis connection: `redis-cli ping`
   - Check CELERY_BROKER_URL in configuration

2. **Tasks not processing**:
   - Ensure Celery worker is running
   - Check worker logs for errors
   - Verify task names match between definition and call

3. **Database connection errors in tasks**:
   - Ensure PostgreSQL is accessible from Celery worker
   - Check DATABASE_URL configuration
   - Verify database session handling in tasks

4. **Import errors**:
   - Ensure app module is in Python path
   - Check virtual environment is activated
   - Verify all dependencies installed

## Monitoring and Debugging

1. **Flower Dashboard** (http://localhost:5555):
   - Monitor active workers
   - View task execution history
   - Check task failures and retries

2. **Celery Logs**:
   - Worker startup information
   - Task execution details
   - Error messages and tracebacks

3. **Redis CLI**:
   ```bash
   # Connect to Redis
   redis-cli
   
   # Check keys
   KEYS *
   
   # Monitor commands
   MONITOR
   ```

## Next Steps
Once Phase 3 is complete and all tests are passing, proceed to Phase 4 for Docker containerization. 