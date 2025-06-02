#!/usr/bin/env python3

import os
import sys
import requests

# Setup environment
project_root = "/app"
os.chdir(project_root)
sys.path.insert(0, project_root)
os.environ["USE_APIFY_CLIENT_MOCK"] = "true"

from app.core.config import settings

API_BASE = f"http://localhost:8000{settings.API_V1_STR}"

def debug_circuit_breaker_detection():
    """Debug why circuit breaker detection isn't working."""
    
    print("🔍 DEBUG: Circuit Breaker Detection")
    print("=" * 50)
    
    try:
        # Import functions
        from app.background_services.smoke_tests.test_concurrent_campaigns_flow import (
            signup_and_login, 
            check_circuit_breaker_status,
            check_campaigns_paused_by_circuit_breaker
        )
        
        # Get authentication
        token, email = signup_and_login()
        print(f"✅ Authenticated as: {email}")
        
        # Test 1: Circuit breaker status endpoint
        print(f"\n🔧 Test 1: Circuit Breaker Status Endpoint")
        print("-" * 40)
        
        cb_status = check_circuit_breaker_status(token)
        print(f"📊 Raw CB Status: {cb_status}")
        
        if cb_status:
            print(f"📊 CB Status Keys: {list(cb_status.keys())}")
            if "data" in cb_status:
                print(f"📊 CB Data Keys: {list(cb_status['data'].keys())}")
                if "circuit_breakers" in cb_status["data"]:
                    circuit_breakers = cb_status["data"]["circuit_breakers"]
                    print(f"📊 Circuit Breakers: {list(circuit_breakers.keys())}")
                    
                    for service, status in circuit_breakers.items():
                        print(f"🔧 {service}: {status}")
                        if isinstance(status, dict):
                            state = status.get("circuit_state", "unknown")
                            print(f"   State: {state}")
                            if state != "closed":
                                print(f"   ⚠️  DETECTED OPEN CIRCUIT BREAKER!")
                                print(f"   Issue: {status.get('pause_info', 'No details')}")
        
        # Test 2: Campaign status check 
        print(f"\n🔧 Test 2: Check for Paused Campaigns")
        print("-" * 40)
        
        # Get some campaign IDs from recent activity
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{API_BASE}/campaigns", headers=headers, params={"limit": 10})
        
        if resp.status_code == 200:
            campaigns_data = resp.json()
            print(f"📊 Campaigns response keys: {list(campaigns_data.keys())}")
            
            # Extract campaign IDs
            campaigns = campaigns_data.get("data", {}).get("campaigns", [])
            if not campaigns:
                campaigns = campaigns_data.get("campaigns", [])
            
            print(f"📊 Found {len(campaigns)} campaigns")
            
            if campaigns:
                campaign_ids = [c["id"] for c in campaigns[:5]]  # Check first 5
                print(f"📊 Checking campaigns: {campaign_ids}")
                
                paused_campaigns = check_campaigns_paused_by_circuit_breaker(token, campaign_ids)
                print(f"🛑 Paused campaigns: {len(paused_campaigns)}")
                
                for campaign in paused_campaigns:
                    print(f"   Campaign {campaign['id']}: {campaign['status_message']}")
        
        print(f"\n🔧 Test 3: Manual Circuit Breaker Check")
        print("-" * 40)
        
        # Direct API call to circuit breaker endpoint
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{API_BASE}/queue-management/status", headers=headers)
        print(f"📊 Queue Management Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"📊 Queue Management Response: {data}")
        else:
            print(f"❌ Queue Management Error: {resp.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_circuit_breaker_detection() 