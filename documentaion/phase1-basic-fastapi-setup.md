# Phase 1: Basic FastAPI Setup

## Overview
This phase establishes the foundation of the FastAPI application with basic health check endpoints and project structure.

## Step 1.1: Initialize Project

### AI Agent Instructions:
**Task**: Create the project directory structure and initialize the Python environment.

**Actions to perform**:
1. Create a new directory named `fastapi-k8-proto`
2. Navigate into the directory
3. Initialize a git repository
4. Create a Python virtual environment
5. Create the requirements directory

**Commands to execute**:
```bash
mkdir fastapi-k8-proto
cd fastapi-k8-proto
git init
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
mkdir requirements
```

**Expected outcome**: 
- A new project directory with git initialized
- An activated Python virtual environment
- A requirements directory ready for dependency files

## Step 1.2: Create Requirements Files

### AI Agent Instructions:
**Task**: Create three requirements files for different environments (base, development, and production).

**Action 1**: Create `requirements/base.txt` with the following content:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
```

**Action 2**: Create `requirements/dev.txt` with the following content:
```
-r base.txt
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
flake8==6.1.0
mypy==1.7.0
httpx==0.25.1
```

**Action 3**: Create `requirements/prod.txt` with the following content:
```
-r base.txt
gunicorn==21.2.0
```

**Expected outcome**: Three requirements files created in the requirements directory.

## Step 1.3: Create Basic FastAPI Application

### AI Agent Instructions:
**Task**: Create the basic FastAPI application structure with configuration and health endpoints.

**Action 1**: Create the application directory structure:
```bash
mkdir -p app/api/endpoints
mkdir -p app/core
touch app/__init__.py
touch app/api/__init__.py
touch app/api/endpoints/__init__.py
touch app/core/__init__.py
```

**Action 2**: Create `app/main.py` with the following content:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import jobs, health
from app.core.config import settings

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"])
    app.include_router(jobs.router, prefix=f"{settings.API_V1_STR}/jobs", tags=["jobs"])

    return app

app = create_application()
```

**Action 3**: Create `app/core/config.py` with the following content:
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

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
```

**Action 4**: Create `app/api/endpoints/health.py` with the following content:
```python
from fastapi import APIRouter, status

router = APIRouter()

@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy", "service": "fastapi-k8-proto"}

@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    # TODO: Add database and Redis connectivity checks
    return {"status": "ready"}

@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    return {"status": "alive"}
```

**Action 5**: Create a placeholder `app/api/endpoints/jobs.py` with the following content:
```python
from fastapi import APIRouter

router = APIRouter()

# Placeholder - will be implemented in Phase 3
```

**Expected outcome**: 
- Complete application directory structure
- Main FastAPI application file
- Configuration management
- Health check endpoints

## Step 1.4: Test Basic Setup

### AI Agent Instructions:
**Task**: Install dependencies and test the basic FastAPI application.

**Action 1**: Install the development dependencies:
```bash
pip install -r requirements/dev.txt
```

**Action 2**: Create a `.env` file with basic configuration:
```
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
```

**Action 3**: Run the FastAPI application:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Action 4**: Test the endpoints using curl commands:
```bash
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Test readiness endpoint
curl http://localhost:8000/api/v1/health/ready

# Test liveness endpoint
curl http://localhost:8000/api/v1/health/live

# Check OpenAPI documentation
curl http://localhost:8000/docs
```

**Expected responses**:
- Health endpoint: `{"status":"healthy","service":"fastapi-k8-proto"}`
- Ready endpoint: `{"status":"ready"}`
- Live endpoint: `{"status":"alive"}`
- Docs endpoint: HTML page with Swagger UI

**Action 5**: Create a simple test file `tests/test_health.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "fastapi-k8-proto"}

def test_readiness_check():
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

def test_liveness_check():
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
```

**Action 6**: Run the tests:
```bash
pytest tests/test_health.py -v
```

**Expected outcome**: 
- All tests should pass
- The application should be accessible at http://localhost:8000
- API documentation available at http://localhost:8000/docs

## Phase 1 Completion Checklist

- [ ] Project directory structure created
- [ ] Virtual environment set up and activated
- [ ] All requirements files created
- [ ] FastAPI application structure implemented
- [ ] Configuration management set up
- [ ] Health check endpoints working
- [ ] Basic tests passing
- [ ] API documentation accessible

## Next Steps
Once Phase 1 is complete and all tests are passing, proceed to Phase 2 for database integration. 