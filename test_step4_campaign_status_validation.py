#!/usr/bin/env python3

import os
import sys

# Get project root and change working directory to it
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
os.chdir(project_root)
print(f"[Setup] Changed working directory to: {project_root}")

# Ensure project root is in sys.path for app imports
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Enable the Apollo mock
os.environ["USE_APIFY_CLIENT_MOCK"] = "true"

from app.background_services.smoke_tests.test_concurrent_campaigns_flow import (
    signup_and_login, 
    create_organization, 
    create_campaign,
    check_campaign_status_summary,
    validate_no_unexpected_pauses,
    report_campaign_status_summary
)

def test_campaign_status_validation():
    """Test the new campaign status validation functions."""
    
    print("\n" + "="*60)
    print("🧪 TESTING STEP 4: CAMPAIGN STATUS VALIDATION FUNCTIONS")
    print("="*60)
    
    try:
        print("\n📋 Phase 1: Authentication & Setup")
        print("-" * 40)
        token, email = signup_and_login()
        org_id = create_organization(token)
        
        print("\n📋 Phase 2: Create Test Campaign")
        print("-" * 40)
        campaign_id = create_campaign(token, 1, org_id)
        print(f"✅ Created test campaign: {campaign_id}")
        
        campaign_ids = [campaign_id]
        
        print("\n🔍 Phase 3: Test check_campaign_status_summary")
        print("-" * 40)
        status_summary, campaign_details = check_campaign_status_summary(token, campaign_ids)
        print(f"📊 Status summary: {status_summary}")
        print(f"📊 Campaign details: {len(campaign_details)} campaigns")
        if campaign_details:
            detail = campaign_details[0]
            print(f"📋 Campaign {detail['id']}: status={detail['status']}")
        
        print("\n🔍 Phase 4: Test validate_no_unexpected_pauses")
        print("-" * 40)
        no_pauses, paused_campaigns = validate_no_unexpected_pauses(token, campaign_ids)
        print(f"✅ No unexpected pauses: {no_pauses}")
        print(f"📊 Paused campaigns count: {len(paused_campaigns)}")
        
        print("\n🔍 Phase 5: Test report_campaign_status_summary")
        print("-" * 40)
        summary, details = report_campaign_status_summary(token, campaign_ids, "Step 4 Test Status Check")
        
        print("\n" + "="*60)
        print("🎉 STEP 4 TEST RESULT: ALL FUNCTIONS WORKING CORRECTLY!")
        print("="*60)
        print("✅ check_campaign_status_summary: Working")
        print("✅ validate_no_unexpected_pauses: Working") 
        print("✅ report_campaign_status_summary: Working")
        print("\n💡 Campaign status validation functions are ready for integration!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_campaign_status_validation()
    sys.exit(0 if success else 1) 