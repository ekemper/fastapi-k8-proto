# Enhanced Concurrent Campaigns Test Implementation Plan

## Executive Summary

This document provides a focused implementation plan for enhancing the existing `test_concurrent_campaigns_flow.py` to be aware of circuit breaker states and respond appropriately when service failures occur during test execution. The goal is to make the test more robust and provide clear reporting when the circuit breaker triggers, while maintaining focus on happy path execution.

## General Implementation Rules and Instructions

### Critical Guidelines for AI Agent Implementation

1. **Technical Assessment**: Always make a technical, critical assessment for any queries, statements, ideas, questions. Don't be afraid to question the user's plan.

2. **Clarification Required**: Always ask for more clarification if needed from the user when implementing the steps of the plan.

3. **Evidence-Based Decisions**: NEVER MAKE SHIT UP - always provide rationale for a decision.

4. **Code Implementation**: In cases where there are code edits, the ai agent is to perform the changes.

5. **Command Execution**: In cases where there are commands to be run, the ai agent is to run them in the chat window context and parse the output for errors and other actionable information.

6. **Migration Handling**: When creating and running migrations, run the commands in the API docker container.

7. **Testing Protocol**: Pay particular attention to the API testing logic (routes, service, model, tests). Always run the tests after making changes to the API.

8. **Individual Test Execution**: When running individual tests, run them in the API docker container: use `docker exec fastapi-k8-proto-api-1 pytest...`

9. **Full Test Suite**: When running the whole suite of tests, use `make docker-test`.

10. **Functional Testing Focus**: We need comprehensive functional API layer tests - the tests should hit the API and then check the database for results.

11. **Test Updates**: When planning code edits, plan to update the tests immediately.

12. **Environment Variables**: To assess what environment variables are used in the application you can run `cat .env`.

13. **Configuration Management**: DO NOT create or modify or otherwise manipulate the env files. If there are configuration values that need to be updated or modified, ask the user to add or change something.

14. **Database/Redis Commands**: If there is a script or command that will need a connection to postgres or redis, the command or script should be run in the API docker container.

15. **Docker Commands**: Before creating a command that uses a container name, please run `docker ps` to get the correct name.

16. **Docker Compose Version**: Never use the deprecated `docker-compose` command version. Always use the newer `docker compose` command version.

17. **Documentation**: For the plan you create, please create a md document in the root of the project and put the instructions there for safe keeping.

## Current System Understanding

### What We Have
- Existing concurrent campaigns test that validates happy path execution
- Circuit breaker system that can pause campaigns when services fail
- Campaign status includes PAUSED state when circuit breaker triggers
- Queue management system that pauses jobs when services are unavailable

### What We Need
- Test awareness of circuit breaker states during execution
- Graceful handling when campaigns get paused due to service failures
- Clear reporting on what went wrong and why the test stopped
- Ability to detect if the system is in a paused state

## Implementation Steps

### Step 1: Add Circuit Breaker Status Monitoring

**Goal**: Add utilities to check circuit breaker status and detect service failures during test execution.

**Actions**:
1. Add function to check circuit breaker status via API
2. Add function to check if campaigns have been paused due to circuit breaker
3. Add periodic circuit breaker health checks during test execution
4. Add clear error reporting for circuit breaker failures

**Verification Strategy**:
- Test circuit breaker status endpoint access
- Verify detection of paused campaigns
- Test error reporting clarity

**Implementation Details**:
```python
def check_circuit_breaker_status(token):
    """Check current circuit breaker status for all services."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(f"{API_BASE}/queue-management/status", headers=headers)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[Circuit Breaker] Warning: Could not get status: {resp.status_code}")
            return None
    except Exception as e:
        print(f"[Circuit Breaker] Warning: Status check failed: {e}")
        return None

def check_campaigns_paused_by_circuit_breaker(token, campaign_ids):
    """Check if any campaigns have been paused due to circuit breaker events."""
    headers = {"Authorization": f"Bearer {token}"}
    paused_campaigns = []
    
    for campaign_id in campaign_ids:
        try:
            resp = requests.get(f"{API_BASE}/campaigns/{campaign_id}", headers=headers)
            if resp.status_code == 200:
                campaign = resp.json().get("data", resp.json())
                if campaign["status"] == "PAUSED":
                    paused_campaigns.append({
                        "id": campaign_id,
                        "status_message": campaign.get("status_message", ""),
                        "paused_reason": campaign.get("status_error", "")
                    })
        except Exception as e:
            print(f"[Circuit Breaker] Warning: Could not check campaign {campaign_id}: {e}")
    
    return paused_campaigns

def report_circuit_breaker_failure(cb_status, paused_campaigns):
    """Generate clear report when circuit breaker causes test failure."""
    print("\n" + "="*80)
    print("❌ TEST STOPPED: CIRCUIT BREAKER TRIGGERED")
    print("="*80)
    
    if cb_status:
        print("\n🔍 Circuit Breaker Status:")
        for service, status in cb_status.get("data", {}).items():
            if isinstance(status, dict):
                state = status.get("circuit_state", "unknown")
                if state != "closed":
                    print(f"  ⚠️  {service.upper()}: {state}")
                    if status.get("pause_info"):
                        print(f"      Reason: {status['pause_info']}")
    
    if paused_campaigns:
        print(f"\n📊 Campaigns Paused: {len(paused_campaigns)}")
        for campaign in paused_campaigns:
            print(f"  🛑 Campaign {campaign['id']}")
            if campaign["status_message"]:
                print(f"      Message: {campaign['status_message']}")
            if campaign["paused_reason"]:
                print(f"      Reason: {campaign['paused_reason']}")
    
    print("\n💡 This indicates a real service failure occurred during testing.")
    print("💡 Check service health and retry the test when services are restored.")
    print("="*80)
```

---

### Step 2: Enhance Job Monitoring with Circuit Breaker Awareness

**Goal**: Update the job monitoring functions to detect and handle circuit breaker events gracefully.

**Actions**:
1. Modify `monitor_all_campaigns_jobs` to check for circuit breaker triggers
2. Add circuit breaker status checks during job polling
3. Update timeout handling to distinguish between normal delays and service failures
4. Add early termination when circuit breaker opens

**Verification Strategy**:
- Test monitoring behavior when services are healthy
- Test detection of circuit breaker events during monitoring
- Verify appropriate early termination and reporting

**Implementation Details**:
```python
def monitor_all_campaigns_jobs_with_cb_awareness(token, campaigns_data, timeout=600):
    """Enhanced monitoring that detects circuit breaker events and reports gracefully."""
    
    print(f"\n[Monitor] Starting enhanced monitoring with circuit breaker awareness")
    print(f"[Monitor] Will check for service failures every 30 seconds")
    
    campaign_ids = list(campaigns_data.keys())
    start_time = time.time()
    last_cb_check = 0
    cb_check_interval = 30  # Check circuit breaker every 30 seconds
    
    # Initialize tracking
    job_tracker = {}
    for campaign_id, data in campaigns_data.items():
        job_tracker[campaign_id] = {
            'campaign_index': data['campaign_index'],
            'expected_jobs': data['leads_count'],
            'completed_jobs': 0,
            'failed_jobs': 0,
            'status': 'waiting'
        }
    
    while time.time() - start_time < timeout:
        current_time = time.time()
        elapsed = current_time - start_time
        
        # Periodic circuit breaker health check
        if elapsed - last_cb_check >= cb_check_interval:
            print(f"\n[Monitor] Performing circuit breaker health check at {elapsed:.0f}s...")
            
            # Check circuit breaker status
            cb_status = check_circuit_breaker_status(token)
            
            # Check if campaigns have been paused
            paused_campaigns = check_campaigns_paused_by_circuit_breaker(token, campaign_ids)
            
            if paused_campaigns:
                print(f"\n[Monitor] ⚠️  CIRCUIT BREAKER TRIGGERED - {len(paused_campaigns)} campaigns paused")
                report_circuit_breaker_failure(cb_status, paused_campaigns)
                return None  # Return None to indicate circuit breaker failure
            
            last_cb_check = elapsed
        
        # Continue with normal job monitoring
        all_complete = True
        for campaign_id, tracking in job_tracker.items():
            if tracking['status'] in ['completed', 'failed']:
                continue
                
            # Check jobs for this campaign
            jobs = fetch_campaign_jobs(token, campaign_id)
            enrich_jobs = [j for j in jobs if j["job_type"] == "ENRICH_LEAD"]
            
            completed = [j for j in enrich_jobs if j["status"] == "COMPLETED"]
            failed = [j for j in enrich_jobs if j["status"] == "FAILED"]
            
            tracking['completed_jobs'] = len(completed)
            tracking['failed_jobs'] = len(failed)
            
            # Update status
            if tracking['failed_jobs'] > 0:
                tracking['status'] = 'failed'
            elif tracking['completed_jobs'] >= tracking['expected_jobs']:
                tracking['status'] = 'completed'
            
            if tracking['status'] not in ['completed', 'failed']:
                all_complete = False
        
        if all_complete:
            print(f"\n[Monitor] ✅ All campaigns completed successfully after {elapsed:.1f}s")
            return job_tracker
            
        time.sleep(3)
    
    # Timeout reached - check if it's due to circuit breaker
    print(f"\n[Monitor] Timeout reached - performing final circuit breaker check...")
    paused_campaigns = check_campaigns_paused_by_circuit_breaker(token, campaign_ids)
    
    if paused_campaigns:
        cb_status = check_circuit_breaker_status(token)
        report_circuit_breaker_failure(cb_status, paused_campaigns)
        return None
    else:
        # Normal timeout
        print(f"\n[Monitor] ⏰ Normal timeout reached after {timeout}s")
        return job_tracker
```

---

### Step 3: Update Main Test Flow with Circuit Breaker Handling

**Goal**: Modify the main test function to handle circuit breaker events gracefully and provide clear reporting.

**Actions**:
1. Replace standard job monitoring with circuit breaker-aware version
2. Add clear differentiation between test failures and service failures
3. Update error reporting to be more informative
4. Add test result categorization (success, service failure, test failure)

**Verification Strategy**:
- Test normal happy path execution
- Test behavior when circuit breaker triggers
- Verify clear distinction between failure types

**Implementation Details**:
```python
def main():
    """Enhanced main test function with circuit breaker awareness."""
    
    print("\n" + "="*80)
    print("🚀 STARTING CONCURRENT CAMPAIGNS TEST WITH CIRCUIT BREAKER AWARENESS")
    print("📊 Testing normal campaign execution with service failure detection")
    print("📊 Will stop and report clearly if circuit breaker triggers")
    print("="*80)
    
    try:
        # Phase 1: Setup (unchanged)
        token, email = signup_and_login()
        organization_id = create_organization(token)
        
        # Phase 2: Initial circuit breaker health check
        print(f"\n🔍 PHASE 1: Pre-test Circuit Breaker Health Check")
        print("-" * 50)
        cb_status = check_circuit_breaker_status(token)
        if cb_status:
            unhealthy_services = []
            for service, status in cb_status.get("data", {}).items():
                if isinstance(status, dict) and status.get("circuit_state") != "closed":
                    unhealthy_services.append(service)
            
            if unhealthy_services:
                print(f"⚠️  WARNING: Services not healthy: {', '.join(unhealthy_services)}")
                print("⚠️  Test may fail due to existing service issues")
                print("⚠️  Consider waiting for services to recover before running test")
        
        # Phase 3: Campaign creation (unchanged)
        print(f"\n📋 PHASE 2: Sequential Campaign Creation")
        print("-" * 50)
        campaigns_data = create_campaigns_sequentially(
            token, 
            organization_id, 
            NUM_CAMPAIGNS, 
            LEADS_PER_CAMPAIGN
        )
        
        # Phase 4: Process validation (unchanged)
        print(f"\n🔍 PHASE 3: Process Integrity Validation")
        print("-" * 50)
        validate_campaign_data(campaigns_data)
        
        # Phase 5: Enhanced concurrent monitoring
        print(f"\n⚡ PHASE 4: Concurrent Job Monitoring with Circuit Breaker Awareness")
        print("-" * 50)
        job_results = monitor_all_campaigns_jobs_with_cb_awareness(
            token, campaigns_data, CAMPAIGN_TIMEOUT
        )
        
        # Phase 6: Results analysis
        if job_results is None:
            # Circuit breaker triggered
            print(f"\n📊 TEST RESULT: SERVICE FAILURE DETECTED")
            print("✅ Test successfully detected and reported service failure")
            print("✅ Circuit breaker integration working correctly")
            return False  # Indicate service failure, not test failure
        else:
            # Normal completion
            print(f"\n📊 PHASE 5: End-to-End Process Analysis")
            print("-" * 50)
            analyze_process_results(campaigns_data, job_results)
            
            print("\n" + "="*80)
            print("🎉 CONCURRENT CAMPAIGNS TEST COMPLETED SUCCESSFULLY!")
            print("✅ Happy path execution validated")
            print("✅ No service failures detected")
            print("✅ All campaigns processed successfully")
            print("="*80)
            
            return True
        
    except Exception as e:
        # Check if it's a circuit breaker related failure
        try:
            campaign_ids = list(campaigns_data.keys()) if 'campaigns_data' in locals() else []
            paused_campaigns = check_campaigns_paused_by_circuit_breaker(token, campaign_ids)
            
            if paused_campaigns:
                cb_status = check_circuit_breaker_status(token)
                report_circuit_breaker_failure(cb_status, paused_campaigns)
                return False  # Service failure
            else:
                print(f"\n❌ TEST FAILED: {e}")
                raise  # Re-raise if not circuit breaker related
        except:
            print(f"\n❌ TEST FAILED: {e}")
            raise
    finally:
        cleanup_test_data()

if __name__ == "__main__":
    try:
        success = main()
        if success:
            sys.exit(0)  # Normal success
        else:
            sys.exit(2)  # Service failure (different from test failure)
    except Exception:
        sys.exit(1)  # Test failure
```

---

### Step 4: Add Campaign Status Validation

**Goal**: Add utilities to validate campaign status and detect pause reasons during test execution.

**Actions**:
1. Add campaign status checking utilities
2. Implement pause reason validation
3. Add campaign state history tracking during test
4. Create campaign status summary reporting

**Verification Strategy**:
- Test campaign status detection accuracy
- Verify pause reason identification
- Test status change detection during execution

**Implementation Details**:
```python
def check_campaign_status_summary(token, campaign_ids):
    """Get summary of campaign statuses for reporting."""
    headers = {"Authorization": f"Bearer {token}"}
    status_summary = {
        "CREATED": 0,
        "RUNNING": 0, 
        "PAUSED": 0,
        "COMPLETED": 0,
        "FAILED": 0
    }
    
    campaign_details = []
    
    for campaign_id in campaign_ids:
        try:
            resp = requests.get(f"{API_BASE}/campaigns/{campaign_id}", headers=headers)
            if resp.status_code == 200:
                campaign = resp.json().get("data", resp.json())
                status = campaign["status"]
                status_summary[status] = status_summary.get(status, 0) + 1
                
                campaign_details.append({
                    "id": campaign_id,
                    "status": status,
                    "status_message": campaign.get("status_message", ""),
                    "status_error": campaign.get("status_error", "")
                })
        except Exception as e:
            print(f"[Status Check] Warning: Could not check campaign {campaign_id}: {e}")
    
    return status_summary, campaign_details

def validate_no_unexpected_pauses(token, campaign_ids):
    """Check that no campaigns were unexpectedly paused during execution."""
    status_summary, campaign_details = check_campaign_status_summary(token, campaign_ids)
    
    if status_summary.get("PAUSED", 0) > 0:
        paused_campaigns = [c for c in campaign_details if c["status"] == "PAUSED"]
        print(f"\n⚠️  WARNING: {len(paused_campaigns)} campaigns are in PAUSED status")
        
        for campaign in paused_campaigns:
            print(f"   Campaign {campaign['id']}: {campaign['status_message']}")
        
        return False, paused_campaigns
    
    return True, []
```

## Success Criteria

### Functional Requirements Met
- [ ] Test detects circuit breaker events during execution
- [ ] Test reports clearly when services fail
- [ ] Test distinguishes between service failures and test failures  
- [ ] Test continues to validate happy path when services are healthy
- [ ] Test provides actionable information when failures occur

### Technical Requirements Met  
- [ ] Circuit breaker status monitoring works correctly
- [ ] Campaign pause detection is accurate
- [ ] Error reporting is clear and informative
- [ ] Test execution is reliable for happy path scenarios
- [ ] Exit codes properly indicate failure types

### Operational Requirements Met
- [ ] Test output clearly indicates what happened
- [ ] Service failure reports include actionable information
- [ ] Test can be used for continuous monitoring of system health
- [ ] Results differentiate between expected and unexpected failures

## Conclusion

This focused enhancement makes the existing concurrent campaigns test more robust by adding circuit breaker awareness without changing its core purpose of validating happy path execution. The test will now:

1. **Detect service failures** early and report them clearly
2. **Stop execution gracefully** when circuit breaker triggers
3. **Provide actionable information** about what services failed
4. **Distinguish between** service failures and actual test failures
5. **Continue to validate** the happy path when services are healthy

The implementation is minimal and focused, adding just enough circuit breaker awareness to make the test resilient and informative without turning it into a comprehensive circuit breaker testing suite. 