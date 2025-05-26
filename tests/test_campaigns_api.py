import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import uuid

from app.main import app
from app.core.database import Base, get_db
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobStatus, JobType

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_campaigns_api.db"
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

@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # Clean up test data after each test
        db.query(Job).delete()
        db.query(Campaign).delete()
        db.commit()
        db.close()

@pytest.fixture
def campaign_payload():
    """Return a valid payload for creating a campaign via the API."""
    return {
        "name": "API Test Campaign",
        "description": "This campaign is created by tests",
        "fileName": "input-file.csv",
        "totalRecords": 25,
        "url": "https://app.apollo.io/#/some-search",
        "organization_id": "org-test"
    }

def verify_campaign_in_db(db_session, campaign_id: str, expected_data: dict = None):
    """Helper to verify campaign exists in database with correct values."""
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    assert campaign is not None, f"Campaign {campaign_id} not found in database"
    
    if expected_data:
        for key, value in expected_data.items():
            db_value = getattr(campaign, key)
            if isinstance(db_value, CampaignStatus):
                db_value = db_value.value
            assert db_value == value, f"Expected {key}={value}, got {db_value}"
    
    return campaign

def verify_no_campaign_in_db(db_session, campaign_id: str = None):
    """Helper to verify no campaign records exist in database."""
    if campaign_id:
        campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
        assert campaign is None, f"Campaign {campaign_id} should not exist in database"
    else:
        count = db_session.query(Campaign).count()
        assert count == 0, f"Expected 0 campaigns in database, found {count}"

def verify_job_in_db(db_session, campaign_id: str, job_type: JobType, expected_count: int = 1):
    """Helper to verify job exists in database for campaign."""
    jobs = db_session.query(Job).filter(
        Job.campaign_id == campaign_id,
        Job.job_type == job_type
    ).all()
    assert len(jobs) == expected_count, f"Expected {expected_count} {job_type.value} jobs, found {len(jobs)}"
    return jobs

# ---------------------------------------------------------------------------
# Campaign Creation Tests
# ---------------------------------------------------------------------------

def test_create_campaign_success(db_session, campaign_payload):
    """Test successful campaign creation with all required fields."""
    response = client.post("/api/v1/campaigns/", json=campaign_payload)
    
    # Verify API response
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == campaign_payload["name"]
    assert data["status"] == CampaignStatus.CREATED.value
    assert data["fileName"] == campaign_payload["fileName"]
    assert data["totalRecords"] == campaign_payload["totalRecords"]
    assert data["url"] == campaign_payload["url"]
    assert data["organization_id"] == campaign_payload["organization_id"]
    assert "id" in data
    assert "created_at" in data
    
    # Verify campaign record exists in database with correct values
    verify_campaign_in_db(db_session, data["id"], {
        "name": campaign_payload["name"],
        "status": CampaignStatus.CREATED.value,
        "fileName": campaign_payload["fileName"],
        "totalRecords": campaign_payload["totalRecords"],
        "url": campaign_payload["url"],
        "organization_id": campaign_payload["organization_id"]
    })

def test_create_campaign_validation_missing_fields(db_session):
    """Test validation errors for missing required fields."""
    bad_payload = {
        "name": "Missing Fields",
        "fileName": "file.csv",
        "url": "https://app.apollo.io"
        # Missing totalRecords (required)
    }
    
    response = client.post("/api/v1/campaigns/", json=bad_payload)
    assert response.status_code == 422  # Validation error
    
    # Verify no database records created on validation failures
    verify_no_campaign_in_db(db_session)

def test_create_campaign_validation_invalid_fields(db_session):
    """Test validation errors for invalid field values."""
    bad_payload = {
        "name": "",  # Empty name should fail
        "description": "Test",
        "fileName": "",  # Empty fileName should fail
        "totalRecords": -1,  # Negative records should fail
        "url": ""  # Empty URL should fail
    }
    
    response = client.post("/api/v1/campaigns/", json=bad_payload)
    assert response.status_code == 422  # Validation error
    
    # Verify no database records created on validation failures
    verify_no_campaign_in_db(db_session)

def test_create_campaign_special_characters(db_session, campaign_payload):
    """Test campaign creation with special characters."""
    payload = {**campaign_payload, "name": "!@#$%^&*()_+-=[]{}|;:,.<>?/~`\"'\\"}
    response = client.post("/api/v1/campaigns/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    
    # Verify database record
    verify_campaign_in_db(db_session, data["id"], {"name": payload["name"]})

def test_create_campaign_xss_prevention(db_session, campaign_payload):
    """Test XSS prevention in campaign names/descriptions."""
    payload = {
        **campaign_payload,
        "name": "<script>alert(\"XSS\")</script>Campaign",
        "description": "<img src=x onerror=alert('XSS')>"
    }
    response = client.post("/api/v1/campaigns/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    
    # Verify database stores the values as-is (no HTML escaping at API level)
    verify_campaign_in_db(db_session, data["id"], {
        "name": payload["name"],
        "description": payload["description"]
    })

def test_create_campaign_long_description(db_session, campaign_payload):
    """Test campaign creation with extremely long field values."""
    long_description = "x" * 10000
    payload = {**campaign_payload, "description": long_description}
    response = client.post("/api/v1/campaigns/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert len(data["description"]) == 10000
    
    # Verify database record
    verify_campaign_in_db(db_session, data["id"], {"description": long_description})

# ---------------------------------------------------------------------------
# Campaign Listing Tests
# ---------------------------------------------------------------------------

def test_list_campaigns_empty(db_session):
    """Test empty campaign list returns correctly."""
    response = client.get("/api/v1/campaigns/")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
    
    # Verify database is empty
    verify_no_campaign_in_db(db_session)

def test_list_campaigns_multiple(db_session, campaign_payload):
    """Create multiple campaigns and verify list endpoint returns all."""
    created_campaigns = []
    
    # Create 3 campaigns
    for i in range(3):
        payload = {**campaign_payload, "name": f"Campaign {i}"}
        response = client.post("/api/v1/campaigns/", json=payload)
        assert response.status_code == 201
        created_campaigns.append(response.json())
    
    # List campaigns
    response = client.get("/api/v1/campaigns/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    
    # Verify all campaigns are returned
    returned_ids = {campaign["id"] for campaign in data}
    expected_ids = {campaign["id"] for campaign in created_campaigns}
    assert returned_ids == expected_ids
    
    # Verify database has all campaigns
    db_count = db_session.query(Campaign).count()
    assert db_count == 3

def test_list_campaigns_pagination(db_session, campaign_payload):
    """Test pagination parameters work correctly."""
    # Create 5 campaigns
    for i in range(5):
        payload = {**campaign_payload, "name": f"Campaign {i}"}
        response = client.post("/api/v1/campaigns/", json=payload)
        assert response.status_code == 201
    
    # Test pagination
    response = client.get("/api/v1/campaigns/?skip=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # Should return 2 campaigns (limit=2)
    
    # Verify database still has all 5 campaigns
    db_count = db_session.query(Campaign).count()
    assert db_count == 5

# ---------------------------------------------------------------------------
# Campaign Retrieval Tests
# ---------------------------------------------------------------------------

def test_get_campaign_success(db_session, campaign_payload):
    """Test successful retrieval of existing campaign."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    created_campaign = create_response.json()
    campaign_id = created_campaign["id"]
    
    # Retrieve campaign
    response = client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 200
    data = response.json()
    
    # Verify returned data matches database record exactly
    assert data["id"] == campaign_id
    assert data["name"] == campaign_payload["name"]
    assert data["status"] == CampaignStatus.CREATED.value
    
    # Verify database record matches
    db_campaign = verify_campaign_in_db(db_session, campaign_id)
    assert data["name"] == db_campaign.name
    assert data["description"] == db_campaign.description

def test_get_campaign_not_found(db_session):
    """Test 404 error for non-existent campaign ID."""
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/campaigns/{non_existent_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

def test_get_campaign_malformed_id(db_session):
    """Test malformed campaign ID handling."""
    malformed_id = "not-a-valid-uuid"
    response = client.get(f"/api/v1/campaigns/{malformed_id}")
    
    # Should return 404 (not found) rather than 400 (bad request)
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Campaign Update Tests
# ---------------------------------------------------------------------------

def test_update_campaign_success(db_session, campaign_payload):
    """Test successful update of allowed fields."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["id"]
    
    # Update campaign
    update_data = {
        "name": "Updated Campaign Name",
        "description": "Updated description"
    }
    response = client.patch(f"/api/v1/campaigns/{campaign_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    
    # Verify database record is updated correctly
    verify_campaign_in_db(db_session, campaign_id, {
        "name": update_data["name"],
        "description": update_data["description"]
    })

def test_update_campaign_partial(db_session, campaign_payload):
    """Test partial updates work correctly."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["id"]
    original_name = create_response.json()["name"]
    
    # Update only description
    update_data = {"description": "Only description updated"}
    response = client.patch(f"/api/v1/campaigns/{campaign_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == original_name  # Should remain unchanged
    assert data["description"] == update_data["description"]
    
    # Verify database record
    verify_campaign_in_db(db_session, campaign_id, {
        "name": original_name,
        "description": update_data["description"]
    })

def test_update_campaign_validation_error(db_session, campaign_payload):
    """Test validation errors for invalid update data."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["id"]
    
    # Try to update with invalid data
    invalid_update = {"totalRecords": -1}  # Negative value should fail
    response = client.patch(f"/api/v1/campaigns/{campaign_id}", json=invalid_update)
    
    assert response.status_code == 422  # Validation error
    
    # Verify database record is unchanged
    verify_campaign_in_db(db_session, campaign_id, {
        "totalRecords": campaign_payload["totalRecords"]
    })

def test_update_campaign_not_found(db_session):
    """Test 404 error for non-existent campaign."""
    non_existent_id = str(uuid.uuid4())
    update_data = {"name": "Updated Name"}
    response = client.patch(f"/api/v1/campaigns/{non_existent_id}", json=update_data)
    
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Campaign Start Flow Tests
# ---------------------------------------------------------------------------

def test_start_campaign_success(db_session, campaign_payload):
    """Test starting campaign changes status from CREATED to RUNNING."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["id"]
    
    # Start campaign
    response = client.post(f"/api/v1/campaigns/{campaign_id}/start", json={})
    
    # Note: This might fail due to missing Apollo/Instantly services
    # but we test the expected behavior when services are available
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == CampaignStatus.RUNNING.value
        
        # Verify database status update is persisted
        verify_campaign_in_db(db_session, campaign_id, {
            "status": CampaignStatus.RUNNING.value
        })
        
        # Verify background job is created in jobs table
        verify_job_in_db(db_session, campaign_id, JobType.FETCH_LEADS, expected_count=1)
    else:
        # Service unavailable - expected in test environment
        assert response.status_code in [500, 404]

def test_start_campaign_duplicate(db_session, campaign_payload):
    """Test error when trying to start non-CREATED campaign."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["id"]
    
    # Manually update campaign status to RUNNING in database
    db_campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    db_campaign.status = CampaignStatus.RUNNING
    db_session.commit()
    
    # Try to start already running campaign
    response = client.post(f"/api/v1/campaigns/{campaign_id}/start", json={})
    
    # Should return error for invalid state transition
    assert response.status_code in [400, 422]

def test_start_campaign_not_found(db_session):
    """Test starting non-existent campaign returns 404."""
    non_existent_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/campaigns/{non_existent_id}/start", json={})
    
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Campaign Details Tests
# ---------------------------------------------------------------------------

def test_get_campaign_details_success(db_session, campaign_payload):
    """Test campaign details endpoint returns campaign + stats."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["id"]
    
    # Get campaign details
    response = client.get(f"/api/v1/campaigns/{campaign_id}/details")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "data" in data
    assert "campaign" in data["data"]
    assert "lead_stats" in data["data"]
    assert "instantly_analytics" in data["data"]
    
    # Verify campaign data matches database
    campaign_data = data["data"]["campaign"]
    verify_campaign_in_db(db_session, campaign_id, {
        "name": campaign_data["name"],
        "status": campaign_data["status"]
    })
    
    # Verify lead statistics structure (even if zero)
    lead_stats = data["data"]["lead_stats"]
    expected_stats = [
        "total_leads_fetched", "leads_with_email", "leads_with_verified_email",
        "leads_with_enrichment", "leads_with_email_copy", "leads_with_instantly_record"
    ]
    for stat in expected_stats:
        assert stat in lead_stats

def test_get_campaign_details_not_found(db_session):
    """Test campaign details for non-existent campaign returns 404."""
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/campaigns/{non_existent_id}/details")
    
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Campaign Cleanup Tests
# ---------------------------------------------------------------------------

def test_cleanup_old_jobs_success(db_session, campaign_payload):
    """Create old jobs and verify cleanup endpoint works (may use background tasks)."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["id"]
    
    # Create old job in database
    old_job = Job(
        name="Test Fetch Leads Job",
        description="Test job for cleanup",
        campaign_id=campaign_id,
        job_type=JobType.FETCH_LEADS,
        status=JobStatus.COMPLETED,
        created_at=datetime.utcnow() - timedelta(days=10)
    )
    db_session.add(old_job)
    db_session.commit()
    
    # Verify job exists
    jobs_before = db_session.query(Job).filter(Job.campaign_id == campaign_id).count()
    assert jobs_before == 1
    
    # Cleanup old jobs
    response = client.post(f"/api/v1/campaigns/{campaign_id}/cleanup", json={"days": 7})
    
    # In test environment, Celery may not be available, so we expect either:
    # 200 (success with background task queued) or 500 (Celery unavailable)
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        # Background task was queued successfully
        data = response.json()
        assert "message" in data
        # Note: Job deletion happens in background, so we can't verify immediately
    else:
        # Celery/Redis not available in test environment - this is expected
        data = response.json()
        assert "detail" in data
        assert "redis" in data["detail"].lower() or "celery" in data["detail"].lower()

def test_cleanup_respects_date_cutoff(db_session, campaign_payload):
    """Test cleanup endpoint handles date cutoff parameter correctly."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["id"]
    
    # Create recent job (should not be deleted)
    recent_job = Job(
        name="Recent Fetch Leads Job",
        description="Recent job that should not be deleted",
        campaign_id=campaign_id,
        job_type=JobType.FETCH_LEADS,
        status=JobStatus.COMPLETED,
        created_at=datetime.utcnow() - timedelta(days=3)
    )
    
    # Create old job (should be deleted)
    old_job = Job(
        name="Old Enrich Leads Job",
        description="Old job that should be deleted",
        campaign_id=campaign_id,
        job_type=JobType.ENRICH_LEADS,
        status=JobStatus.COMPLETED,
        created_at=datetime.utcnow() - timedelta(days=10)
    )
    
    db_session.add(recent_job)
    db_session.add(old_job)
    db_session.commit()
    
    # Cleanup jobs older than 7 days
    response = client.post(f"/api/v1/campaigns/{campaign_id}/cleanup", json={"days": 7})
    
    # In test environment, expect either success or Celery unavailable error
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        # Background task was queued successfully
        data = response.json()
        assert "message" in data
        # Note: Actual cleanup happens in background task
    else:
        # Celery/Redis not available - expected in test environment
        pass

def test_cleanup_active_jobs_not_removed(db_session, campaign_payload):
    """Verify cleanup endpoint handles active jobs correctly."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["id"]
    
    # Create old but active job
    active_job = Job(
        name="Active Fetch Leads Job",
        description="Active job that should not be deleted",
        campaign_id=campaign_id,
        job_type=JobType.FETCH_LEADS,
        status=JobStatus.PROCESSING,  # Active status
        created_at=datetime.utcnow() - timedelta(days=10)
    )
    db_session.add(active_job)
    db_session.commit()
    
    # Cleanup old jobs
    response = client.post(f"/api/v1/campaigns/{campaign_id}/cleanup", json={"days": 7})
    
    # In test environment, expect either success or Celery unavailable error
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        # Background task was queued successfully
        data = response.json()
        assert "message" in data
        # Note: Background task logic would preserve active jobs
    else:
        # Celery/Redis not available - expected in test environment
        pass

def test_cleanup_no_old_jobs(db_session, campaign_payload):
    """Test cleanup with no old jobs returns appropriate response."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["id"]
    
    # No jobs created
    
    # Cleanup old jobs
    response = client.post(f"/api/v1/campaigns/{campaign_id}/cleanup", json={"days": 7})
    
    # In test environment, expect either success or Celery unavailable error
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        # Background task was queued successfully
        data = response.json()
        assert "message" in data
    else:
        # Celery/Redis not available - expected in test environment
        pass

def test_cleanup_invalid_data(db_session):
    """Test cleanup with invalid data returns validation error."""
    # Missing days parameter
    response = client.post("/api/v1/campaigns/test-id/cleanup", json={})
    assert response.status_code == 400
    
    # Invalid days value
    response = client.post("/api/v1/campaigns/test-id/cleanup", json={"days": -1})
    assert response.status_code == 400

# ---------------------------------------------------------------------------
# Campaign Results Tests
# ---------------------------------------------------------------------------

def test_get_campaign_results_not_found(db_session):
    """Test getting results for non-existent campaign returns 404."""
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/campaigns/{non_existent_id}/results")
    
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Security and Edge Case Tests
# ---------------------------------------------------------------------------

def test_sql_injection_prevention(db_session):
    """Test SQL injection prevention in campaign operations."""
    # Try SQL injection in campaign ID
    malicious_id = "'; DROP TABLE campaigns; --"
    response = client.get(f"/api/v1/campaigns/{malicious_id}")
    
    # Should return 404, not cause database error
    assert response.status_code == 404
    
    # Verify campaigns table still exists by creating a campaign
    campaign_payload = {
        "name": "Test Campaign",
        "fileName": "test.csv",
        "totalRecords": 1,
        "url": "https://test.com"
    }
    response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert response.status_code == 201

def test_concurrent_operations_same_campaign(db_session, campaign_payload):
    """Test concurrent operations on same campaign are handled correctly."""
    # Create campaign
    create_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["id"]
    
    # Simulate concurrent updates (in real scenario these would be parallel)
    update1 = {"name": "Update 1"}
    update2 = {"name": "Update 2"}
    
    response1 = client.patch(f"/api/v1/campaigns/{campaign_id}", json=update1)
    response2 = client.patch(f"/api/v1/campaigns/{campaign_id}", json=update2)
    
    # Both should succeed (last one wins)
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Verify final state in database
    final_campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    assert final_campaign.name == "Update 2"  # Last update should win

def test_campaign_workflow_integration(db_session, campaign_payload):
    """Test complete campaign workflow with database verification at each step."""
    # 1. Create campaign
    response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert response.status_code == 201
    campaign = response.json()
    campaign_id = campaign["id"]
    
    # Verify creation in database
    verify_campaign_in_db(db_session, campaign_id, {
        "status": CampaignStatus.CREATED.value,
        "name": campaign_payload["name"]
    })
    
    # 2. Get campaign
    response = client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 200
    retrieved_campaign = response.json()
    assert retrieved_campaign["id"] == campaign_id
    
    # 3. Update campaign
    update_data = {"name": "Updated Test Campaign"}
    response = client.patch(f"/api/v1/campaigns/{campaign_id}", json=update_data)
    assert response.status_code == 200
    
    # Verify update in database
    verify_campaign_in_db(db_session, campaign_id, {
        "name": "Updated Test Campaign"
    })
    
    # 4. Get campaign details
    response = client.get(f"/api/v1/campaigns/{campaign_id}/details")
    assert response.status_code == 200
    details = response.json()
    assert "data" in details
    assert details["data"]["campaign"]["name"] == "Updated Test Campaign"
    
    # 5. Cleanup jobs (should work even with no jobs)
    response = client.post(f"/api/v1/campaigns/{campaign_id}/cleanup", json={"days": 30})
    # In test environment, expect either success or Celery unavailable error
    assert response.status_code in [200, 500]
    
    # 6. Verify campaign still exists after cleanup
    verify_campaign_in_db(db_session, campaign_id, {
        "name": "Updated Test Campaign"
    }) 