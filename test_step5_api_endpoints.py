#!/usr/bin/env python3
"""
Test Step 5: API Endpoints for Campaign Pausing
Tests the new API endpoints added for bulk campaign operations and campaign status.
"""

import asyncio
import sys
import os
sys.path.append('/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.organization import Organization
from app.models.campaign import Campaign, CampaignStatus
from app.models.job import Job, JobStatus, JobType
from app.core.circuit_breaker import ThirdPartyService
from app.core.config import settings
import requests
import json


def setup_test_data(db):
    """Setup test organization and campaigns for API testing."""
    print("Setting up test data...")
    
    # Clean up any existing test data
    db.query(Campaign).filter(Campaign.name.like("Step 5 Test%")).delete()
    db.query(Organization).filter(Organization.id == "test-org-step5").delete()
    db.commit()
    
    # Create test organization
    test_org = Organization(
        id="test-org-step5",
        name="Test Org Step 5",
        description="Testing organization for Step 5 API endpoints"
    )
    db.add(test_org)
    db.commit()
    print("✓ Created test organization")
    
    # Create test campaigns
    campaigns = []
    statuses = [CampaignStatus.RUNNING, CampaignStatus.RUNNING, CampaignStatus.PAUSED, CampaignStatus.CREATED]
    
    for i, status in enumerate(statuses):
        campaign = Campaign(
            name=f"Step 5 Test Campaign {i+1}",
            description=f"Testing API endpoints {i+1}",
            organization_id="test-org-step5",
            fileName=f"test_step5_{i+1}.csv",
            totalRecords=50 + i*10,
            url=f"https://app.apollo.io/step5-test-{i+1}",
            status=status
        )
        
        # For paused campaign, add relevant status message
        if status == CampaignStatus.PAUSED:
            campaign.status_message = "Campaign paused: Service apollo unavailable: Test pause reason"
            
        campaigns.append(campaign)
    
    db.add_all(campaigns)
    db.commit()
    print(f"✓ Created {len(campaigns)} test campaigns with various statuses")
    
    return campaigns


def test_campaign_status_endpoint():
    """Test GET /queue-management/campaign-status endpoint."""
    print("\n--- Test 1: Campaign Status Endpoint ---")
    
    try:
        response = requests.get("http://localhost:8000/api/v1/queue-management/campaign-status")
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success", "Expected success status"
            
            campaign_data = data["data"]
            assert "totals" in campaign_data, "Expected totals in response"
            assert "campaigns_by_status" in campaign_data, "Expected campaigns_by_status in response"
            assert "paused_by_service" in campaign_data, "Expected paused_by_service in response"
            
            totals = campaign_data["totals"]
            print(f"✓ Total campaigns: {totals['total_campaigns']}")
            print(f"✓ Running: {totals['running']}, Paused: {totals['paused']}, Created: {totals['created']}")
            
            # Check paused by service analysis
            paused_by_service = campaign_data["paused_by_service"]
            if "apollo" in paused_by_service:
                print(f"✓ Found {len(paused_by_service['apollo'])} campaigns paused due to apollo")
            
            print("✓ Campaign status endpoint working correctly")
            
        else:
            print(f"✗ Campaign status endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"✗ Error testing campaign status endpoint: {str(e)}")


def test_paused_campaigns_for_service():
    """Test GET /queue-management/paused-campaigns/{service} endpoint."""
    print("\n--- Test 2: Paused Campaigns for Service Endpoint ---")
    
    try:
        # Test with apollo service
        response = requests.get("http://localhost:8000/api/v1/queue-management/paused-campaigns/apollo")
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success", "Expected success status"
            
            campaign_data = data["data"]
            assert "service" in campaign_data, "Expected service in response"
            assert "paused_campaigns" in campaign_data, "Expected paused_campaigns in response"
            assert "count" in campaign_data, "Expected count in response"
            
            print(f"✓ Service: {campaign_data['service']}")
            print(f"✓ Paused campaigns count: {campaign_data['count']}")
            
            paused_campaigns = campaign_data["paused_campaigns"]
            for campaign in paused_campaigns:
                print(f"  - Campaign {campaign['name']}: {campaign['status_message']}")
                
            print("✓ Paused campaigns for service endpoint working correctly")
            
        else:
            print(f"✗ Paused campaigns endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"✗ Error testing paused campaigns endpoint: {str(e)}")


def test_bulk_campaign_pause():
    """Test POST /queue-management/pause-campaigns-for-service endpoint."""
    print("\n--- Test 3: Bulk Campaign Pause Endpoint ---")
    
    try:
        # Prepare request data
        pause_data = {
            "service": "perplexity",
            "reason": "Test bulk pause via API"
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/queue-management/pause-campaigns-for-service",
            json=pause_data
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success", "Expected success status"
            
            campaign_data = data["data"]
            assert "service" in campaign_data, "Expected service in response"
            assert "campaigns_paused" in campaign_data, "Expected campaigns_paused in response"
            
            print(f"✓ Service: {campaign_data['service']}")
            print(f"✓ Campaigns paused: {campaign_data['campaigns_paused']}")
            print(f"✓ Reason: {campaign_data['reason']}")
            print(f"✓ Message: {campaign_data['message']}")
            
            print("✓ Bulk campaign pause endpoint working correctly")
            
        else:
            print(f"✗ Bulk campaign pause failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"✗ Error testing bulk campaign pause: {str(e)}")


def test_bulk_campaign_resume():
    """Test POST /queue-management/resume-campaigns-for-service endpoint."""
    print("\n--- Test 4: Bulk Campaign Resume Endpoint ---")
    
    try:
        # Prepare request data
        resume_data = {
            "service": "apollo"
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/queue-management/resume-campaigns-for-service",
            json=resume_data
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success", "Expected success status"
            
            campaign_data = data["data"]
            assert "service" in campaign_data, "Expected service in response"
            assert "campaigns_eligible" in campaign_data, "Expected campaigns_eligible in response"
            assert "campaigns_resumed" in campaign_data, "Expected campaigns_resumed in response"
            
            print(f"✓ Service: {campaign_data['service']}")
            print(f"✓ Campaigns eligible: {campaign_data['campaigns_eligible']}")
            print(f"✓ Campaigns resumed: {campaign_data['campaigns_resumed']}")
            print(f"✓ Message: {campaign_data['message']}")
            
            print("✓ Bulk campaign resume endpoint working correctly")
            
        else:
            print(f"✗ Bulk campaign resume failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"✗ Error testing bulk campaign resume: {str(e)}")


def test_integrated_service_pause():
    """Test POST /queue-management/pause-service endpoint (updated with campaign handling)."""
    print("\n--- Test 5: Integrated Service Pause Endpoint ---")
    
    try:
        # Prepare request data
        pause_data = {
            "service": "openai",
            "reason": "Test integrated service pause"
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/queue-management/pause-service",
            json=pause_data
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success", "Expected success status"
            
            service_data = data["data"]
            assert "service" in service_data, "Expected service in response"
            assert "paused" in service_data, "Expected paused in response"
            assert "jobs_paused" in service_data, "Expected jobs_paused in response"
            assert "campaigns_paused" in service_data, "Expected campaigns_paused in response"
            
            print(f"✓ Service: {service_data['service']}")
            print(f"✓ Paused: {service_data['paused']}")
            print(f"✓ Jobs paused: {service_data['jobs_paused']}")
            print(f"✓ Campaigns paused: {service_data['campaigns_paused']}")
            print(f"✓ Message: {service_data['message']}")
            
            print("✓ Integrated service pause endpoint working correctly")
            
        else:
            print(f"✗ Integrated service pause failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"✗ Error testing integrated service pause: {str(e)}")


def test_integrated_service_resume():
    """Test POST /queue-management/resume-service endpoint (updated with campaign handling)."""
    print("\n--- Test 6: Integrated Service Resume Endpoint ---")
    
    try:
        # Prepare request data
        resume_data = {
            "service": "openai"
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/queue-management/resume-service",
            json=resume_data
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success", "Expected success status"
            
            service_data = data["data"]
            assert "service" in service_data, "Expected service in response"
            assert "resumed" in service_data, "Expected resumed in response"
            assert "jobs_resumed" in service_data, "Expected jobs_resumed in response"
            assert "campaigns_eligible" in service_data, "Expected campaigns_eligible in response"
            assert "campaigns_resumed" in service_data, "Expected campaigns_resumed in response"
            
            print(f"✓ Service: {service_data['service']}")
            print(f"✓ Resumed: {service_data['resumed']}")
            print(f"✓ Jobs resumed: {service_data['jobs_resumed']}")
            print(f"✓ Campaigns eligible: {service_data['campaigns_eligible']}")
            print(f"✓ Campaigns resumed: {service_data['campaigns_resumed']}")
            print(f"✓ Message: {service_data['message']}")
            
            print("✓ Integrated service resume endpoint working correctly")
            
        else:
            print(f"✗ Integrated service resume failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"✗ Error testing integrated service resume: {str(e)}")


def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\n--- Test 7: Error Handling ---")
    
    try:
        # Test invalid service name
        pause_data = {
            "service": "invalid_service",
            "reason": "Test error handling"
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/queue-management/pause-campaigns-for-service",
            json=pause_data
        )
        
        if response.status_code == 400:
            print("✓ Invalid service name properly rejected")
        else:
            print(f"✗ Expected 400 for invalid service, got {response.status_code}")
            
        # Test invalid service for paused campaigns endpoint
        response = requests.get("http://localhost:8000/api/v1/queue-management/paused-campaigns/invalid_service")
        
        if response.status_code == 400:
            print("✓ Invalid service in GET endpoint properly rejected")
        else:
            print(f"✗ Expected 400 for invalid service in GET, got {response.status_code}")
            
        print("✓ Error handling working correctly")
        
    except Exception as e:
        print(f"✗ Error testing error handling: {str(e)}")


def cleanup_test_data(db):
    """Clean up test data."""
    print("\n--- Cleanup ---")
    try:
        db.query(Campaign).filter(Campaign.name.like("Step 5 Test%")).delete()
        db.query(Organization).filter(Organization.id == "test-org-step5").delete()
        db.commit()
        print("✓ Cleaned up test data")
    except Exception as e:
        print(f"✗ Error cleaning up: {str(e)}")


async def main():
    """Main test function."""
    print("="*60)
    print("Testing Step 5: API Endpoints for Campaign Pausing")
    print("="*60)
    
    # Setup database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Setup test data
        campaigns = setup_test_data(db)
        
        # Run all tests
        test_campaign_status_endpoint()
        test_paused_campaigns_for_service()
        test_bulk_campaign_pause()
        test_bulk_campaign_resume()
        test_integrated_service_pause()
        test_integrated_service_resume()
        test_error_handling()
        
        print("\n" + "="*60)
        print("Step 5 API Endpoints Testing Complete!")
        print("="*60)
        
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
    finally:
        cleanup_test_data(db)
        db.close()


if __name__ == "__main__":
    asyncio.run(main()) 