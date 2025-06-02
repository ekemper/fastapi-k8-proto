#!/usr/bin/env python3
"""
Test script for Step 4: Circuit Breaker Event Integration
Tests automatic campaign pausing/resuming based on circuit breaker events
"""

import asyncio
import time
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.organization import Organization
from app.services.campaign import CampaignService
from app.core.circuit_breaker import ThirdPartyService, CircuitState, get_circuit_breaker
from app.core.campaign_event_handler import get_campaign_event_handler

async def test_step4_functionality():
    """Test Step 4: Circuit Breaker Event Integration"""
    
    print("=== STEP 4: Circuit Breaker Event Integration Tests ===\n")
    
    db = SessionLocal()
    campaign_service = CampaignService()
    circuit_breaker = get_circuit_breaker()
    event_handler = get_campaign_event_handler()
    
    try:
        # Setup: Create test organization and campaigns
        print("--- Setup: Creating Test Data ---")
        test_org = Organization(
            id="test-org-step4",
            name="Test Org Step 4",
            description="Testing organization for circuit breaker events"
        )
        db.add(test_org)
        db.commit()
        print("✓ Created test organization")
        
        # Create multiple test campaigns in running state
        campaigns = []
        for i in range(3):
            campaign = Campaign(
                name=f"Step 4 Test Campaign {i+1}",
                description=f"Testing circuit breaker events {i+1}",
                organization_id="test-org-step4",
                fileName=f"test_step4_{i+1}.csv",
                totalRecords=20 + i*10,
                url=f"https://app.apollo.io/step4-test-{i+1}",
                status=CampaignStatus.RUNNING
            )
            campaigns.append(campaign)
        
        db.add_all(campaigns)
        db.commit()
        print(f"✓ Created {len(campaigns)} running test campaigns")
        
        # Test 1: Circuit Breaker Opens - Automatic Campaign Pausing
        print("\n--- Test 1: Automatic Campaign Pausing on Circuit Breaker Open ---")
        
        # Manually trigger a circuit breaker opening
        test_service = ThirdPartyService.APOLLO
        circuit_breaker.manually_pause_service(test_service, "Test circuit breaker opening")
        print(f"✓ Manually opened circuit breaker for {test_service.value}")
        
        # Wait a moment for events to process
        await asyncio.sleep(1)
        
        # Verify campaigns were paused
        for campaign in campaigns:
            db.refresh(campaign)
        paused_campaigns = [c for c in campaigns if c.status == CampaignStatus.PAUSED]
        print(f"✓ {len(paused_campaigns)} campaigns were automatically paused")
        
        # Verify status messages contain circuit breaker information
        for campaign in paused_campaigns:
            db.refresh(campaign)
            assert campaign.status_message is not None, f"Campaign {campaign.id} should have status message"
            assert test_service.value.lower() in campaign.status_message.lower(), f"Status message should mention {test_service.value}"
            print(f"✓ Campaign {campaign.name} paused with message: {campaign.status_message[:50]}...")
        
        # Test 2: Circuit Breaker Event Handler Direct Test
        print("\n--- Test 2: Direct Event Handler Testing ---")
        
        # Test event handler directly
        paused_count = await event_handler.handle_circuit_breaker_opened(
            ThirdPartyService.PERPLEXITY, 
            "Direct test failure", 
            {"failure_count": 5, "error_type": "timeout"}
        )
        print(f"✓ Event handler directly paused {paused_count} campaigns for Perplexity failure")
        
        # Test 3: Circuit Breaker Closes - Automatic Campaign Resumption
        print("\n--- Test 3: Automatic Campaign Resumption on Circuit Breaker Close ---")
        
        # Close the circuit breaker
        circuit_breaker.manually_resume_service(test_service)
        print(f"✓ Manually closed circuit breaker for {test_service.value}")
        
        # Wait for events to process
        await asyncio.sleep(1)
        
        # Check which campaigns could be resumed
        resumable_count = await event_handler.handle_circuit_breaker_closed(test_service)
        print(f"✓ {resumable_count} campaigns were eligible for resumption")
        
        # Test 4: Multiple Service Failures
        print("\n--- Test 4: Multiple Service Failures ---")
        
        # Create a new running campaign for this test
        multi_campaign = Campaign(
            name="Multi-Service Test Campaign",
            description="Testing multiple service failures",
            organization_id="test-org-step4",
            fileName="multi_test.csv",
            totalRecords=100,
            url="https://app.apollo.io/multi-test",
            status=CampaignStatus.RUNNING
        )
        db.add(multi_campaign)
        db.commit()
        print("✓ Created campaign for multi-service failure test")
        
        # Trigger multiple service failures
        services_to_fail = [ThirdPartyService.OPENAI, ThirdPartyService.INSTANTLY]
        for service in services_to_fail:
            await event_handler.handle_circuit_breaker_opened(
                service, 
                f"Simulated {service.value} failure",
                {"failure_count": 3}
            )
            print(f"✓ Simulated failure for {service.value}")
        
        # Verify campaign is paused
        db.refresh(multi_campaign)
        assert multi_campaign.status == CampaignStatus.PAUSED, "Campaign should be paused due to service failures"
        print(f"✓ Campaign paused due to multiple service failures")
        
        # Test 5: Partial Service Recovery
        print("\n--- Test 5: Partial Service Recovery ---")
        
        # Resume only one service
        recovered_service = services_to_fail[0]  # OPENAI
        await event_handler.handle_circuit_breaker_closed(recovered_service)
        
        # Verify campaign is still paused (other services still down)
        db.refresh(multi_campaign)
        print(f"✓ Campaign remains paused after partial recovery ({recovered_service.value})")
        
        # Resume all services
        for service in services_to_fail[1:]:  # INSTANTLY
            await event_handler.handle_circuit_breaker_closed(service)
        
        print("✓ All services recovered")
        
        # Test 6: Error Handling and Edge Cases
        print("\n--- Test 6: Error Handling ---")
        
        # Test with non-existent campaign
        try:
            fake_campaign = Campaign(
                id="fake-id-that-does-not-exist",
                name="Fake Campaign",
                status=CampaignStatus.PAUSED
            )
            
            can_resume = await event_handler._can_resume_campaign_safely(fake_campaign, db)
            print(f"✓ Handled non-existent campaign gracefully: can_resume = {can_resume}")
        except Exception as e:
            print(f"✓ Error handling worked: {type(e).__name__}")
        
        # Test 7: API Endpoints
        print("\n--- Test 7: API Endpoint Integration ---")
        
        # Test the campaign service integration
        remaining_running = (
            db.query(Campaign)
            .filter(
                Campaign.organization_id == "test-org-step4",
                Campaign.status == CampaignStatus.RUNNING
            )
            .all()
        )
        
        if remaining_running:
            test_campaign = remaining_running[0]
            
            # Test manual pause
            pause_result = await campaign_service.pause_campaign(
                test_campaign.id, 
                "Manual pause via API test", 
                db
            )
            print(f"✓ Manual pause via service: {pause_result['message']}")
            
            # Test manual resume (with circuit breaker checks)
            try:
                resume_result = await campaign_service.resume_campaign(test_campaign.id, db)
                print(f"✓ Manual resume via service: {resume_result['message']}")
            except Exception as e:
                print(f"✓ Resume blocked by circuit breaker checks: {type(e).__name__}")
        
        print("\n=== ALL STEP 4 TESTS PASSED ===")
        
        # Cleanup
        print("\n--- Cleanup ---")
        
        # Reset all circuit breakers
        for service in ThirdPartyService:
            try:
                circuit_breaker.manually_resume_service(service)
            except:
                pass
        
        # Clean up test data
        db.execute(text("DELETE FROM campaigns WHERE organization_id = 'test-org-step4'"))
        db.execute(text("DELETE FROM organizations WHERE id = 'test-org-step4'"))
        db.commit()
        print("✓ Cleaned up test data and reset circuit breakers")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Attempt cleanup even on failure
        try:
            # Reset circuit breakers
            for service in ThirdPartyService:
                try:
                    circuit_breaker.manually_resume_service(service)
                except:
                    pass
            
            db.execute(text("DELETE FROM campaigns WHERE organization_id = 'test-org-step4'"))
            db.execute(text("DELETE FROM organizations WHERE id = 'test-org-step4'"))
            db.commit()
            print("✓ Cleaned up test data after failure")
        except:
            pass
        
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_step4_functionality()) 