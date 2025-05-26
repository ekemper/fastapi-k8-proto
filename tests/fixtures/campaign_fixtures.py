"""
Comprehensive pytest fixtures for campaign API testing.

This module provides all necessary fixtures for testing campaign functionality,
including database sessions, test data, and common testing scenarios.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobStatus, JobType
from tests.helpers.database_helpers import DatabaseHelpers

# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_fixtures.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)

def override_get_db():
    """Override the database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# Database Session Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_db_session():
    """
    Create a fresh database session for each test.
    
    This fixture provides proper transaction isolation and cleanup.
    Each test gets a clean database state.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # Rollback any uncommitted transactions
        db.rollback()
        # Clean up test data
        db.query(Job).delete()
        db.query(Campaign).delete()
        db.commit()
        db.close()


@pytest.fixture(scope="function")
def clean_database(test_db_session):
    """
    Ensure database is clean before and after each test.
    
    This fixture provides additional cleanup guarantees and
    can be used when explicit database cleaning is needed.
    """
    # Clean before test
    test_db_session.query(Job).delete()
    test_db_session.query(Campaign).delete()
    test_db_session.commit()
    
    yield test_db_session
    
    # Clean after test
    test_db_session.query(Job).delete()
    test_db_session.query(Campaign).delete()
    test_db_session.commit()


@pytest.fixture(scope="function")
def db_helpers(test_db_session):
    """Create DatabaseHelpers instance for testing."""
    return DatabaseHelpers(test_db_session)


@pytest.fixture(scope="function")
def api_client():
    """Create FastAPI test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Campaign Data Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_campaign_data():
    """
    Valid campaign creation data for testing.
    
    Returns a dictionary with all required fields for campaign creation.
    """
    return {
        "name": "Test Campaign",
        "description": "A comprehensive test campaign for API testing",
        "fileName": "test_leads.csv",
        "totalRecords": 100,
        "url": "https://app.apollo.io/test-campaign",
        "organization_id": "test-org-123"
    }


@pytest.fixture
def invalid_campaign_data():
    """
    Various invalid data scenarios for testing validation.
    
    Returns a dictionary of different invalid data scenarios.
    """
    return {
        "missing_required_fields": {
            "description": "Missing required fields"
        },
        "empty_name": {
            "name": "",
            "fileName": "test.csv",
            "totalRecords": 100,
            "url": "https://test.com"
        },
        "negative_total_records": {
            "name": "Invalid Records Campaign",
            "fileName": "test.csv",
            "totalRecords": -1,
            "url": "https://test.com"
        },
        "invalid_url": {
            "name": "Invalid URL Campaign",
            "fileName": "test.csv",
            "totalRecords": 100,
            "url": ""
        },
        "name_too_long": {
            "name": "x" * 300,  # Exceeds 255 character limit
            "fileName": "test.csv",
            "totalRecords": 100,
            "url": "https://test.com"
        },
        "invalid_data_types": {
            "name": 123,  # Should be string
            "fileName": "test.csv",
            "totalRecords": "not_a_number",  # Should be integer
            "url": "https://test.com"
        }
    }


@pytest.fixture
def existing_campaign(test_db_session):
    """
    Create a pre-existing campaign in the database for testing.
    
    This fixture creates a campaign that can be used for update,
    delete, and retrieval operations.
    """
    campaign = Campaign(
        id=str(uuid.uuid4()),
        name="Existing Test Campaign",
        description="A campaign that already exists in the database",
        status=CampaignStatus.CREATED,
        fileName="existing_leads.csv",
        totalRecords=250,
        url="https://app.apollo.io/existing-campaign",
        organization_id="existing-org-456"
    )
    
    test_db_session.add(campaign)
    test_db_session.commit()
    test_db_session.refresh(campaign)
    
    return campaign


@pytest.fixture
def multiple_campaigns(test_db_session):
    """
    Create multiple campaigns for list testing and pagination.
    
    Returns a list of campaigns with different statuses and properties.
    """
    campaigns = []
    
    # Create campaigns with different statuses and properties
    campaign_data = [
        {
            "name": "First Campaign",
            "description": "First test campaign",
            "status": CampaignStatus.CREATED,
            "fileName": "first.csv",
            "totalRecords": 50,
            "url": "https://app.apollo.io/first",
            "organization_id": "org-1"
        },
        {
            "name": "Second Campaign",
            "description": "Second test campaign",
            "status": CampaignStatus.RUNNING,
            "fileName": "second.csv",
            "totalRecords": 100,
            "url": "https://app.apollo.io/second",
            "organization_id": "org-2"
        },
        {
            "name": "Third Campaign",
            "description": "Third test campaign",
            "status": CampaignStatus.COMPLETED,
            "fileName": "third.csv",
            "totalRecords": 75,
            "url": "https://app.apollo.io/third",
            "organization_id": "org-1",
            "completed_at": datetime.utcnow()
        },
        {
            "name": "Fourth Campaign",
            "description": "Fourth test campaign",
            "status": CampaignStatus.FAILED,
            "fileName": "fourth.csv",
            "totalRecords": 200,
            "url": "https://app.apollo.io/fourth",
            "organization_id": "org-3",
            "failed_at": datetime.utcnow(),
            "status_error": "Test error message"
        },
        {
            "name": "Fifth Campaign",
            "description": "Fifth test campaign for pagination",
            "status": CampaignStatus.CREATED,
            "fileName": "fifth.csv",
            "totalRecords": 150,
            "url": "https://app.apollo.io/fifth",
            "organization_id": "org-2"
        }
    ]
    
    for data in campaign_data:
        campaign = Campaign(
            id=str(uuid.uuid4()),
            **data
        )
        test_db_session.add(campaign)
        campaigns.append(campaign)
    
    test_db_session.commit()
    
    # Refresh all campaigns
    for campaign in campaigns:
        test_db_session.refresh(campaign)
    
    return campaigns


@pytest.fixture
def campaign_with_jobs(test_db_session):
    """
    Create a campaign with associated jobs for testing job relationships.
    
    Returns a tuple of (campaign, jobs_list).
    """
    # Create campaign
    campaign = Campaign(
        id=str(uuid.uuid4()),
        name="Campaign with Jobs",
        description="A campaign with multiple associated jobs",
        status=CampaignStatus.RUNNING,
        fileName="jobs_test.csv",
        totalRecords=300,
        url="https://app.apollo.io/jobs-test",
        organization_id="jobs-org-789"
    )
    
    test_db_session.add(campaign)
    test_db_session.commit()
    test_db_session.refresh(campaign)
    
    # Create associated jobs
    jobs = []
    job_data = [
        {
            "name": "Fetch Leads Job",
            "description": "Job to fetch leads from Apollo",
            "job_type": JobType.FETCH_LEADS,
            "status": JobStatus.COMPLETED,
            "task_id": f"fetch-{uuid.uuid4()}",
            "result": "Successfully fetched 300 leads",
            "completed_at": datetime.utcnow() - timedelta(hours=2)
        },
        {
            "name": "Enrich Leads Job",
            "description": "Job to enrich lead data",
            "job_type": JobType.ENRICH_LEADS,
            "status": JobStatus.PROCESSING,
            "task_id": f"enrich-{uuid.uuid4()}",
            "result": None
        },
        {
            "name": "Verify Emails Job",
            "description": "Job to verify email addresses",
            "job_type": JobType.VERIFY_EMAILS,
            "status": JobStatus.PENDING,
            "task_id": f"verify-{uuid.uuid4()}",
            "result": None
        },
        {
            "name": "Failed Job",
            "description": "A job that failed during processing",
            "job_type": JobType.GENERATE_EMAIL_COPY,
            "status": JobStatus.FAILED,
            "task_id": f"failed-{uuid.uuid4()}",
            "error": "API rate limit exceeded",
            "completed_at": datetime.utcnow() - timedelta(hours=1)
        }
    ]
    
    for data in job_data:
        job = Job(
            campaign_id=campaign.id,
            **data
        )
        test_db_session.add(job)
        jobs.append(job)
    
    test_db_session.commit()
    
    # Refresh all jobs
    for job in jobs:
        test_db_session.refresh(job)
    
    return campaign, jobs


@pytest.fixture
def old_jobs_for_cleanup(test_db_session):
    """
    Create old jobs for cleanup testing.
    
    Returns campaigns and jobs that are old enough to be cleaned up.
    """
    # Create old campaign
    old_campaign = Campaign(
        id=str(uuid.uuid4()),
        name="Old Campaign for Cleanup",
        description="Campaign with old jobs to be cleaned up",
        status=CampaignStatus.COMPLETED,
        fileName="old_cleanup.csv",
        totalRecords=500,
        url="https://app.apollo.io/old-cleanup",
        organization_id="cleanup-org-999",
        completed_at=datetime.utcnow() - timedelta(days=45)  # 45 days old
    )
    
    test_db_session.add(old_campaign)
    test_db_session.commit()
    test_db_session.refresh(old_campaign)
    
    # Create old jobs (older than 30 days)
    old_jobs = []
    old_job_data = [
        {
            "name": "Old Fetch Job",
            "description": "Old job to be cleaned up",
            "job_type": JobType.FETCH_LEADS,
            "status": JobStatus.COMPLETED,
            "task_id": f"old-fetch-{uuid.uuid4()}",
            "result": "Old completed job",
            "completed_at": datetime.utcnow() - timedelta(days=35)
        },
        {
            "name": "Old Failed Job",
            "description": "Old failed job to be cleaned up",
            "job_type": JobType.ENRICH_LEADS,
            "status": JobStatus.FAILED,
            "task_id": f"old-failed-{uuid.uuid4()}",
            "error": "Old error message",
            "completed_at": datetime.utcnow() - timedelta(days=40)
        }
    ]
    
    for data in old_job_data:
        job = Job(
            campaign_id=old_campaign.id,
            **data
        )
        test_db_session.add(job)
        old_jobs.append(job)
    
    # Create recent campaign and jobs (should not be cleaned up)
    recent_campaign = Campaign(
        id=str(uuid.uuid4()),
        name="Recent Campaign",
        description="Campaign with recent jobs that should not be cleaned up",
        status=CampaignStatus.COMPLETED,
        fileName="recent.csv",
        totalRecords=100,
        url="https://app.apollo.io/recent",
        organization_id="recent-org-111",
        completed_at=datetime.utcnow() - timedelta(days=5)  # 5 days old
    )
    
    test_db_session.add(recent_campaign)
    test_db_session.commit()
    test_db_session.refresh(recent_campaign)
    
    # Create recent jobs (should not be cleaned up)
    recent_jobs = []
    recent_job_data = [
        {
            "name": "Recent Job",
            "description": "Recent job that should not be cleaned up",
            "job_type": JobType.FETCH_LEADS,
            "status": JobStatus.COMPLETED,
            "task_id": f"recent-{uuid.uuid4()}",
            "result": "Recent completed job",
            "completed_at": datetime.utcnow() - timedelta(days=3)
        }
    ]
    
    for data in recent_job_data:
        job = Job(
            campaign_id=recent_campaign.id,
            **data
        )
        test_db_session.add(job)
        recent_jobs.append(job)
    
    test_db_session.commit()
    
    # Refresh all objects
    for job in old_jobs + recent_jobs:
        test_db_session.refresh(job)
    
    return {
        "old_campaign": old_campaign,
        "old_jobs": old_jobs,
        "recent_campaign": recent_campaign,
        "recent_jobs": recent_jobs
    }


# ---------------------------------------------------------------------------
# Specialized Data Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def campaign_update_data():
    """
    Valid data for testing campaign updates.
    
    Returns various update scenarios.
    """
    return {
        "partial_update": {
            "name": "Updated Campaign Name",
            "description": "Updated description"
        },
        "status_update": {
            "status": CampaignStatus.RUNNING,
            "status_message": "Campaign is now running"
        },
        "complete_update": {
            "name": "Completely Updated Campaign",
            "description": "Completely updated description",
            "fileName": "updated_file.csv",
            "totalRecords": 500,
            "url": "https://app.apollo.io/updated",
            "organization_id": "updated-org-999"
        },
        "error_status_update": {
            "status": CampaignStatus.FAILED,
            "status_error": "Test error occurred",
            "failed_at": datetime.utcnow()
        }
    }


@pytest.fixture
def pagination_test_data():
    """
    Data for testing pagination scenarios.
    
    Returns parameters for various pagination tests.
    """
    return {
        "first_page": {"skip": 0, "limit": 2},
        "second_page": {"skip": 2, "limit": 2},
        "large_limit": {"skip": 0, "limit": 100},
        "zero_limit": {"skip": 0, "limit": 0},
        "negative_skip": {"skip": -1, "limit": 10},
        "out_of_bounds": {"skip": 1000, "limit": 10}
    }


@pytest.fixture
def search_filter_data():
    """
    Data for testing search and filtering functionality.
    
    Returns various search and filter scenarios.
    """
    return {
        "by_status": {"status": CampaignStatus.CREATED},
        "by_organization": {"organization_id": "org-1"},
        "by_name_pattern": {"name_contains": "Test"},
        "by_date_range": {
            "created_after": datetime.utcnow() - timedelta(days=7),
            "created_before": datetime.utcnow()
        },
        "multiple_filters": {
            "status": CampaignStatus.COMPLETED,
            "organization_id": "org-1"
        }
    }


# ---------------------------------------------------------------------------
# Performance and Load Testing Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def large_dataset_campaigns(test_db_session):
    """
    Create a large dataset of campaigns for performance testing.
    
    Creates 50 campaigns with various properties for load testing.
    """
    campaigns = []
    
    for i in range(50):
        campaign = Campaign(
            id=str(uuid.uuid4()),
            name=f"Load Test Campaign {i+1}",
            description=f"Campaign {i+1} for load testing with index {i}",
            status=CampaignStatus.CREATED if i % 4 == 0 else 
                   CampaignStatus.RUNNING if i % 4 == 1 else
                   CampaignStatus.COMPLETED if i % 4 == 2 else
                   CampaignStatus.FAILED,
            fileName=f"load_test_{i+1}.csv",
            totalRecords=(i + 1) * 10,
            url=f"https://app.apollo.io/load-test-{i+1}",
            organization_id=f"load-org-{(i % 5) + 1}"  # 5 different orgs
        )
        
        test_db_session.add(campaign)
        campaigns.append(campaign)
        
        # Commit in batches to avoid memory issues
        if (i + 1) % 10 == 0:
            test_db_session.commit()
    
    test_db_session.commit()
    
    # Refresh all campaigns
    for campaign in campaigns:
        test_db_session.refresh(campaign)
    
    return campaigns


# ---------------------------------------------------------------------------
# Error Scenario Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def database_error_scenarios():
    """
    Scenarios for testing database error handling.
    
    Returns various error conditions to test.
    """
    return {
        "duplicate_id": {
            "id": "duplicate-test-id",
            "name": "Duplicate ID Test",
            "fileName": "duplicate.csv",
            "totalRecords": 100,
            "url": "https://test.com"
        },
        "foreign_key_violation": {
            "organization_id": "non-existent-org-id"
        },
        "constraint_violation": {
            "name": None,  # NULL constraint violation
            "fileName": "constraint.csv",
            "totalRecords": 100,
            "url": "https://test.com"
        }
    }


@pytest.fixture
def concurrent_access_data():
    """
    Data for testing concurrent access scenarios.
    
    Returns data for testing race conditions and concurrent operations.
    """
    return {
        "concurrent_updates": [
            {"name": "Concurrent Update 1", "description": "First concurrent update"},
            {"name": "Concurrent Update 2", "description": "Second concurrent update"},
            {"name": "Concurrent Update 3", "description": "Third concurrent update"}
        ],
        "concurrent_status_changes": [
            {"status": CampaignStatus.RUNNING, "status_message": "Started by user 1"},
            {"status": CampaignStatus.FAILED, "status_error": "Failed by user 2"},
            {"status": CampaignStatus.COMPLETED, "status_message": "Completed by user 3"}
        ]
    }


# ---------------------------------------------------------------------------
# Cleanup and Utility Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def auto_cleanup_database():
    """
    Automatically clean database after each test.
    
    This fixture runs automatically and ensures no test data
    leaks between tests.
    """
    yield
    
    # Clean up after test
    db = TestingSessionLocal()
    try:
        db.query(Job).delete()
        db.query(Campaign).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def transaction_rollback_session():
    """
    Database session that automatically rolls back transactions.
    
    Useful for testing database operations without persisting changes.
    """
    db = TestingSessionLocal()
    transaction = db.begin()
    
    try:
        yield db
    finally:
        try:
            if transaction.is_active:
                transaction.rollback()
        except Exception:
            # Transaction might already be closed
            pass
        finally:
            db.close()


@pytest.fixture
def isolated_test_environment(clean_database):
    """
    Completely isolated test environment.
    
    Provides maximum isolation for tests that need guaranteed clean state.
    """
    # Verify database is clean
    assert clean_database.query(Campaign).count() == 0
    assert clean_database.query(Job).count() == 0
    
    yield clean_database
    
    # Verify database is still clean after test
    clean_database.query(Job).delete()
    clean_database.query(Campaign).delete()
    clean_database.commit() 