# Phase 2: Database Integration

## Overview
This phase integrates PostgreSQL database with SQLAlchemy ORM, sets up database models, schemas, and migrations using Alembic.

## Prerequisites
- Phase 1 completed successfully
- PostgreSQL installed locally or accessible via Docker
- Virtual environment activated

## Step 2.1: Update Requirements

### AI Agent Instructions:
**Task**: Add database-related dependencies to the requirements files.

**Action**: Update `requirements/base.txt` by appending the following lines:
```
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
```

**Command to execute**:
```bash
pip install -r requirements/dev.txt
```

**Expected outcome**: All database-related packages installed successfully.

## Step 2.2: Database Configuration

### AI Agent Instructions:
**Task**: Update the configuration file to include database settings.

**Action**: Modify `app/core/config.py` to add database configuration. Replace the entire file with:
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

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
```

**Expected outcome**: Configuration file updated with database settings.

## Step 2.3: Database Setup

### AI Agent Instructions:
**Task**: Create the database connection and session management.

**Action 1**: Create `app/core/database.py` with the following content:
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Action 2**: Start PostgreSQL database (if not already running):
```bash
# Using Docker
docker run -d \
  --name postgres-dev \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=fastapi_k8_proto \
  -p 5432:5432 \
  postgres:15-alpine
```

**Expected outcome**: Database connection module created and PostgreSQL running.

## Step 2.4: Create Models

### AI Agent Instructions:
**Task**: Create SQLAlchemy models for the job tracking system.

**Action 1**: Create the models directory:
```bash
mkdir -p app/models
touch app/models/__init__.py
```

**Action 2**: Create `app/models/job.py` with the following content:
```python
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
```

**Action 3**: Update `app/models/__init__.py`:
```python
from app.models.job import Job, JobStatus

__all__ = ["Job", "JobStatus"]
```

**Expected outcome**: Job model created with all necessary fields.

## Step 2.5: Create Schemas

### AI Agent Instructions:
**Task**: Create Pydantic schemas for request/response validation.

**Action 1**: Create the schemas directory:
```bash
mkdir -p app/schemas
touch app/schemas/__init__.py
```

**Action 2**: Create `app/schemas/job.py` with the following content:
```python
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
```

**Action 3**: Update `app/schemas/__init__.py`:
```python
from app.schemas.job import JobCreate, JobUpdate, JobResponse

__all__ = ["JobCreate", "JobUpdate", "JobResponse"]
```

**Expected outcome**: Pydantic schemas created for data validation.

## Step 2.6: Initialize Alembic

### AI Agent Instructions:
**Task**: Set up Alembic for database migrations.

**Action 1**: Initialize Alembic in the project root:
```bash
alembic init alembic
```

**Action 2**: Update `alembic.ini` file. Find and replace the sqlalchemy.url line:
```ini
sqlalchemy.url = postgresql://postgres:postgres@localhost/fastapi_k8_proto
```

**Action 3**: Replace the content of `alembic/env.py` with:
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import your models
from app.core.database import Base
from app.models import job  # Import all models

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Expected outcome**: Alembic configured and ready to create migrations.

## Step 2.7: Create Initial Migration

### AI Agent Instructions:
**Task**: Create and apply the initial database migration.

**Action 1**: Create the initial migration:
```bash
alembic revision --autogenerate -m "Initial job table"
```

**Action 2**: Review the generated migration file in `alembic/versions/` to ensure it creates the jobs table correctly.

**Action 3**: Apply the migration:
```bash
alembic upgrade head
```

**Action 4**: Verify the database structure:
```bash
# Connect to PostgreSQL
docker exec -it postgres-dev psql -U postgres -d fastapi_k8_proto

# In psql prompt, run:
\dt
\d jobs
\q
```

**Expected outcome**: 
- Migration file created
- Jobs table created in the database
- Table structure matches the model definition

## Step 2.8: Test Database Integration

### AI Agent Instructions:
**Task**: Create tests to verify database integration works correctly.

**Action 1**: Create `tests/test_database.py`:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.models.job import Job, JobStatus
from app.main import app
from fastapi.testclient import TestClient

# Test database
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost/test_db"
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
```

**Action 2**: Run the database tests:
```bash
pytest tests/test_database.py -v
```

**Expected outcome**: All database tests pass successfully.

## Phase 2 Completion Checklist

- [ ] Database dependencies added to requirements
- [ ] Database configuration added to settings
- [ ] Database connection module created
- [ ] PostgreSQL database running
- [ ] Job model created with all fields
- [ ] Pydantic schemas created
- [ ] Alembic initialized and configured
- [ ] Initial migration created and applied
- [ ] Database structure verified
- [ ] Database tests passing

## Troubleshooting

### Common Issues:

1. **PostgreSQL connection error**:
   - Ensure PostgreSQL is running: `docker ps`
   - Check connection parameters in `.env` file
   - Verify PostgreSQL is accessible on port 5432

2. **Migration errors**:
   - Ensure all models are imported in `alembic/env.py`
   - Check database permissions
   - Verify DATABASE_URL is correct

3. **Import errors**:
   - Ensure virtual environment is activated
   - Verify all dependencies are installed
   - Check Python path includes project root

## Next Steps
Once Phase 2 is complete and all tests are passing, proceed to Phase 3 for Redis and Celery integration. 