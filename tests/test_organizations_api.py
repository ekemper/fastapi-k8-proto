import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app.main import app
from app.core.database import Base, get_db
from app.models.organization import Organization
from app.models.campaign import Campaign

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_organizations_api.db"
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
        db.query(Campaign).delete()
        db.query(Organization).delete()
        db.commit()
        db.close()

@pytest.fixture
def organization_payload():
    """Return a valid payload for creating an organization via the API."""
    return {
        "name": "Test Organization",
        "description": "This is a test organization"
    }

def verify_organization_in_db(db_session, org_id: str, expected_data: dict = None):
    """Helper to verify organization exists in database with correct values."""
    org = db_session.query(Organization).filter(Organization.id == org_id).first()
    assert org is not None, f"Organization {org_id} not found in database"
    
    if expected_data:
        for key, value in expected_data.items():
            db_value = getattr(org, key)
            assert db_value == value, f"Expected {key}={value}, got {db_value}"
    
    return org

def verify_no_organization_in_db(db_session, org_id: str = None):
    """Helper to verify no organization records exist in database."""
    if org_id:
        org = db_session.query(Organization).filter(Organization.id == org_id).first()
        assert org is None, f"Organization {org_id} should not exist in database"
    else:
        count = db_session.query(Organization).count()
        assert count == 0, f"Expected 0 organizations in database, found {count}"

# ---------------------------------------------------------------------------
# Organization Creation Tests
# ---------------------------------------------------------------------------

def test_create_organization_success(db_session, organization_payload):
    """Test successful organization creation with all required fields."""
    response = client.post("/api/v1/organizations/", json=organization_payload)
    
    # Verify API response
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == organization_payload["name"]
    assert data["description"] == organization_payload["description"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    # Verify organization record exists in database with correct values
    verify_organization_in_db(db_session, data["id"], {
        "name": organization_payload["name"],
        "description": organization_payload["description"]
    })

def test_create_organization_validation_errors(db_session):
    """Test validation errors for invalid organization data."""
    # Test missing name
    response = client.post("/api/v1/organizations/", json={"description": "No name"})
    assert response.status_code == 422
    
    # Test short name
    response = client.post("/api/v1/organizations/", json={"name": "AB", "description": "Short name"})
    assert response.status_code == 422
    
    # Test missing description
    response = client.post("/api/v1/organizations/", json={"name": "Valid Name"})
    assert response.status_code == 422
    
    # Verify no database records created on validation failures
    verify_no_organization_in_db(db_session)

def test_create_organization_sanitization(db_session):
    """Test input sanitization for XSS prevention."""
    payload = {
        "name": "<script>alert('XSS')</script>Test Org",
        "description": "<img src=x onerror=alert('XSS')>Description"
    }
    response = client.post("/api/v1/organizations/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify HTML tags are removed
    assert "<script>" not in data["name"]
    assert "<img" not in data["description"]
    
    # Verify in database
    org = verify_organization_in_db(db_session, data["id"])
    assert "<script>" not in org.name
    assert "<img" not in org.description

def test_create_organization_special_characters(db_session):
    """Test organization creation with special characters."""
    payload = {
        "name": "Organization & Co. (Test) #1",
        "description": "Special chars: !@#$%^&*()_+-=[]{}|;:,.<>?/~`"
    }
    response = client.post("/api/v1/organizations/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify special characters are preserved (except HTML)
    verify_organization_in_db(db_session, data["id"], {
        "name": data["name"],
        "description": data["description"]
    })

# ---------------------------------------------------------------------------
# Organization Listing Tests
# ---------------------------------------------------------------------------

def test_list_organizations_empty(db_session):
    """Test empty organization list returns correctly."""
    response = client.get("/api/v1/organizations/")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
    
    # Verify database is empty
    verify_no_organization_in_db(db_session)

def test_list_organizations_multiple(db_session, organization_payload):
    """Create multiple organizations and verify list endpoint returns all."""
    created_orgs = []
    
    # Create 3 organizations
    for i in range(3):
        payload = {**organization_payload, "name": f"Organization {i}"}
        response = client.post("/api/v1/organizations/", json=payload)
        assert response.status_code == 201
        created_orgs.append(response.json())
    
    # List organizations
    response = client.get("/api/v1/organizations/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    
    # Verify all organizations are returned
    returned_ids = {org["id"] for org in data}
    expected_ids = {org["id"] for org in created_orgs}
    assert returned_ids == expected_ids
    
    # Verify database has all organizations
    db_count = db_session.query(Organization).count()
    assert db_count == 3

def test_list_organizations_order(db_session, organization_payload):
    """Test organizations are returned in some consistent order."""
    # Create organizations
    created_orgs = []
    for i in range(3):
        payload = {**organization_payload, "name": f"Org {i}"}
        response = client.post("/api/v1/organizations/", json=payload)
        assert response.status_code == 201
        created_orgs.append(response.json())
    
    # List organizations
    response = client.get("/api/v1/organizations/")
    assert response.status_code == 200
    data = response.json()
    
    # Verify we got all organizations
    assert len(data) == 3
    
    # Verify all created organizations are in the response
    created_names = {org["name"] for org in created_orgs}
    returned_names = {org["name"] for org in data}
    assert created_names == returned_names
    
    # Verify organizations have required fields
    for org in data:
        assert "id" in org
        assert "name" in org
        assert "description" in org
        assert "created_at" in org
        assert "updated_at" in org

# ---------------------------------------------------------------------------
# Organization Retrieval Tests
# ---------------------------------------------------------------------------

def test_get_organization_success(db_session, organization_payload):
    """Test successful retrieval of existing organization."""
    # Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    created_org = create_response.json()
    org_id = created_org["id"]
    
    # Retrieve organization
    response = client.get(f"/api/v1/organizations/{org_id}")
    assert response.status_code == 200
    data = response.json()
    
    # Verify returned data matches database record exactly
    assert data["id"] == org_id
    assert data["name"] == organization_payload["name"]
    assert data["description"] == organization_payload["description"]
    assert data["created_at"] == created_org["created_at"]
    assert data["updated_at"] == created_org["updated_at"]
    
    # Verify database record matches
    db_org = verify_organization_in_db(db_session, org_id)
    assert data["name"] == db_org.name
    assert data["description"] == db_org.description

def test_get_organization_not_found(db_session):
    """Test 404 error for non-existent organization ID."""
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/organizations/{non_existent_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

def test_get_organization_malformed_id(db_session):
    """Test malformed organization ID handling."""
    malformed_id = "not-a-valid-uuid"
    response = client.get(f"/api/v1/organizations/{malformed_id}")
    
    # Should return 404 (not found) rather than 400 (bad request)
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Organization Update Tests
# ---------------------------------------------------------------------------

def test_update_organization_success(db_session, organization_payload):
    """Test successful update of organization fields."""
    # Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]
    
    # Update organization
    update_data = {
        "name": "Updated Organization Name",
        "description": "Updated description"
    }
    response = client.put(f"/api/v1/organizations/{org_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    
    # Verify database record is updated correctly
    verify_organization_in_db(db_session, org_id, {
        "name": update_data["name"],
        "description": update_data["description"]
    })

def test_update_organization_partial(db_session, organization_payload):
    """Test partial updates work correctly."""
    # Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]
    original_name = create_response.json()["name"]
    
    # Update only description
    update_data = {"description": "Only description updated"}
    response = client.put(f"/api/v1/organizations/{org_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == original_name  # Should remain unchanged
    assert data["description"] == update_data["description"]
    
    # Verify database record
    verify_organization_in_db(db_session, org_id, {
        "name": original_name,
        "description": update_data["description"]
    })

def test_update_organization_validation_errors(db_session, organization_payload):
    """Test validation errors for invalid update data."""
    # Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]
    
    # Try to update with invalid data
    invalid_updates = [
        {"name": "AB"},  # Too short
        {"name": ""},    # Empty
        {"description": ""}  # Empty description
    ]
    
    for invalid_update in invalid_updates:
        response = client.put(f"/api/v1/organizations/{org_id}", json=invalid_update)
        assert response.status_code in [400, 422]
    
    # Verify database record is unchanged
    verify_organization_in_db(db_session, org_id, {
        "name": organization_payload["name"],
        "description": organization_payload["description"]
    })

def test_update_organization_not_found(db_session):
    """Test 404 error for non-existent organization."""
    non_existent_id = str(uuid.uuid4())
    update_data = {"name": "Updated Name"}
    response = client.put(f"/api/v1/organizations/{non_existent_id}", json=update_data)
    
    assert response.status_code == 404

def test_update_organization_sanitization(db_session, organization_payload):
    """Test input sanitization on updates."""
    # Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]
    
    # Update with HTML content
    update_data = {
        "name": "<b>Bold</b> Organization",
        "description": "<script>alert('XSS')</script>Description"
    }
    response = client.put(f"/api/v1/organizations/{org_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify HTML is sanitized
    assert "<b>" not in data["name"]
    assert "<script>" not in data["description"]

# ---------------------------------------------------------------------------
# Organization-Campaign Relationship Tests
# ---------------------------------------------------------------------------

def test_organization_with_campaigns(db_session, organization_payload):
    """Test organization relationship with campaigns."""
    # Create organization
    org_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]
    
    # Create campaign linked to organization
    campaign_payload = {
        "name": "Test Campaign",
        "description": "Campaign for org test",
        "organization_id": org_id,
        "fileName": "test.csv",
        "totalRecords": 100,
        "url": "https://app.apollo.io/test"
    }
    campaign_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert campaign_response.status_code == 201
    
    # Verify campaign is linked to organization
    campaign_data = campaign_response.json()
    assert campaign_data["organization_id"] == org_id
    
    # Verify in database
    db_campaign = db_session.query(Campaign).filter(Campaign.id == campaign_data["id"]).first()
    assert db_campaign.organization_id == org_id

# ---------------------------------------------------------------------------
# Edge Cases and Error Handling Tests
# ---------------------------------------------------------------------------

def test_concurrent_organization_creation(db_session, organization_payload):
    """Test handling of concurrent organization creation."""
    # This test simulates race conditions by creating organizations rapidly
    import threading
    results = []
    
    def create_org(index):
        payload = {**organization_payload, "name": f"Concurrent Org {index}"}
        response = client.post("/api/v1/organizations/", json=payload)
        results.append(response.status_code)
    
    # Create 5 organizations concurrently
    threads = []
    for i in range(5):
        t = threading.Thread(target=create_org, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # All should succeed
    assert all(status == 201 for status in results)
    
    # Verify all 5 organizations exist in database
    db_count = db_session.query(Organization).count()
    assert db_count == 5

def test_sql_injection_prevention(db_session):
    """Test SQL injection prevention in organization operations."""
    # Try SQL injection in organization name
    malicious_payload = {
        "name": "Org'; DROP TABLE organizations; --",
        "description": "Normal description"
    }
    response = client.post("/api/v1/organizations/", json=malicious_payload)
    
    # Should succeed without executing SQL
    assert response.status_code == 201
    
    # Verify organizations table still exists
    db_count = db_session.query(Organization).count()
    assert db_count == 1
    
    # Try SQL injection in GET request
    malicious_id = "'; DROP TABLE organizations; --"
    response = client.get(f"/api/v1/organizations/{malicious_id}")
    assert response.status_code == 404
    
    # Verify table still exists
    db_count = db_session.query(Organization).count()
    assert db_count == 1

def test_organization_workflow_integration(db_session, organization_payload):
    """Test complete organization workflow: create, read, update, list."""
    # Step 1: Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]
    
    # Step 2: Read organization
    get_response = client.get(f"/api/v1/organizations/{org_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == org_id
    
    # Step 3: Update organization
    update_data = {"name": "Updated via Workflow"}
    update_response = client.put(f"/api/v1/organizations/{org_id}", json=update_data)
    assert update_response.status_code == 200
    assert update_response.json()["name"] == update_data["name"]
    
    # Step 4: List organizations
    list_response = client.get("/api/v1/organizations/")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == org_id
    
    # Verify final state in database
    verify_organization_in_db(db_session, org_id, {
        "name": update_data["name"],
        "description": organization_payload["description"]
    }) 