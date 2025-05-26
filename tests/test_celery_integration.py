import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.workers.tasks import health_check

def test_celery_health_check(client):
    """Test that Celery is configured correctly"""
    # This test requires a running Celery worker
    # For unit tests, we'll just check the task can be called directly
    result = health_check()
    assert result["status"] == "healthy"
    assert "timestamp" in result

def test_create_job_endpoint(client):
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

def test_job_status_endpoint(client):
    """Test job status retrieval"""
    # Create a job
    response = client.post(
        "/api/v1/jobs",
        json={"name": "Status Test Job", "description": "Test description"}
    )
    job_id = response.json()["id"]
    
    # Check status
    response = client.get(f"/api/v1/jobs/{job_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert "status" in data

def test_list_jobs_endpoint(client):
    """Test listing jobs with filters"""
    # List all jobs
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
    # List with status filter
    response = client.get("/api/v1/jobs?status=pending")
    assert response.status_code == 200

def test_cancel_job_endpoint(client):
    """Test job cancellation"""
    # Create a job
    response = client.post(
        "/api/v1/jobs",
        json={"name": "Cancel Test Job", "description": "Test description"}
    )
    job_id = response.json()["id"]
    
    # Cancel it
    response = client.delete(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    assert "cancelled" in response.json()["message"] 