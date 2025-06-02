# Circuit Breaker Graceful Pausing Implementation Plan

## Executive Summary

This document provides a comprehensive step-by-step implementation plan for adding graceful circuit breaker pausing functionality to the FastAPI-K8s-Proto application. When circuit breakers trip due to third-party service failures, the system needs to:

1. **Fix the enum case mismatch**: Job enum uses uppercase 'PAUSED' but database expects lowercase 'paused'
2. **Add campaign pausing capabilities**: New 'paused' status for campaigns with proper state transitions
3. **Implement graceful job pausing**: Update running jobs to paused state when circuits open
4. **Implement graceful campaign pausing**: Update running campaigns to paused state when circuits open
5. **Enforce business rules**: Paused campaigns can be created but not started
6. **Add comprehensive testing**: Full API and integration test coverage

## General Implementation Rules and Instructions

### Critical Guidelines for AI Agent Implementation

1. **Technical Assessment**: Always make a technical, critical assessment for any queries, statements, ideas, questions. Don't be afraid to question the user's plan.

2. **Clarification Required**: Always ask for more clarification if needed from the user when implementing the steps of the plan.

3. **Evidence-Based Decisions**: NEVER MAKE SHIT UP - always provide rationale for a decision.

4. **Code Implementation**: In cases where there are code edits, the AI agent is to perform the changes.

5. **Command Execution**: In cases where there are commands to be run, the AI agent is to run them in the chat window context and parse the output for errors and other actionable information.

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

## Current Architecture Assessment

### Existing Components Analysis

**Models & Enums:**
- `JobStatus` enum: Already includes PAUSED but with **case mismatch** (Python: 'PAUSED', DB: 'paused')
- `CampaignStatus` enum: Missing 'paused' status entirely
- `Campaign` model: Has status transition validation but no paused state support
- `Job` model: Has proper relationships and status handling

**Services & Logic:**
- `CircuitBreakerService`: Comprehensive circuit breaker with service-specific monitoring
- `QueueManager`: Handles job pausing but lacks campaign pausing integration
- `CampaignService`: No circuit breaker integration for pausing running campaigns

**API Endpoints:**
- Queue management endpoints exist for manual service control
- Missing campaign-specific pausing endpoints
- No bulk campaign pausing capabilities

**Testing Patterns:**
- Comprehensive test suite structure exists
- Circuit breaker integration tests present
- Missing tests for campaign pausing scenarios

## Implementation Steps

### Step 1: Fix Critical Enum Case Mismatch

**Goal**: Resolve the database enum case inconsistency causing job pausing failures.

**Actions**:
1. Update the JobStatus enum in `app/models/job.py` to use lowercase 'paused'
2. Create and run a database migration to update the enum value
3. Update any existing code references to use lowercase 'paused'
4. Verify the fix with database queries

**Verification Strategy**:
- Run existing circuit breaker tests to ensure job pausing works
- Execute test query in database to confirm enum compatibility
- Check that failed jobs can now be properly paused

**Implementation Details**:
```python
# Update in app/models/job.py
class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"  # Changed from "PAUSED" to "paused"
```

**Migration Required**: 
- Create migration to update database enum value from 'paused' to handle any case inconsistencies
- Handle any existing data gracefully

---

### Step 2: Add Paused Status to Campaign Model

**Goal**: Extend campaign status enumeration and model to support paused state.

**Actions**:
1. Add PAUSED status to `CampaignStatus` enum
2. Update campaign status transition matrix in `Campaign` model
3. Add pause/resume methods to campaign model
4. Create database migration for new enum value
5. Update campaign schema to support paused status

**Verification Strategy**:
- Run campaign API tests to ensure paused status is accepted
- Test campaign status transitions including pause/resume
- Verify database accepts new enum value

**Implementation Details**:
```python
# Update app/models/campaign_status.py
class CampaignStatus(str, enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"     # New status
    COMPLETED = "completed"
    FAILED = "failed"

# Update app/models/campaign.py transition matrix
VALID_TRANSITIONS = {
    CampaignStatus.CREATED: [CampaignStatus.RUNNING, CampaignStatus.FAILED],
    CampaignStatus.RUNNING: [CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.FAILED],
    CampaignStatus.PAUSED: [CampaignStatus.RUNNING, CampaignStatus.FAILED],  # New transitions
    CampaignStatus.COMPLETED: [],
    CampaignStatus.FAILED: []
}
```

**Migration Required**: 
- Add 'paused' value to campaignstatus enum in database

---

### Step 3: Implement Campaign Pausing Service Logic

**Goal**: Add campaign pausing capabilities to the existing service layer.

**Actions**:
1. Extend `CampaignService` with pause/resume methods
2. Add circuit breaker integration to pause running campaigns
3. Implement bulk campaign pausing by service dependency
4. Add campaign state validation for pausing rules
5. Update campaign status transition handling

**Verification Strategy**:
- Test individual campaign pause/resume operations
- Test bulk campaign pausing when circuit breaker opens
- Verify business rule: paused campaigns cannot be started
- Test campaign state transitions and validation

**Implementation Details**:
```python
# In app/services/campaign.py
async def pause_campaign(self, campaign_id: str, reason: str, db: Session) -> Dict[str, Any]:
    """Pause a running campaign with reason tracking."""
    
async def resume_campaign(self, campaign_id: str, db: Session) -> Dict[str, Any]:
    """Resume a paused campaign."""

async def pause_campaigns_for_service(self, service: ThirdPartyService, reason: str, db: Session) -> int:
    """Pause all running campaigns that depend on a service."""

def can_start_campaign(self, campaign: Campaign) -> tuple[bool, str]:
    """Check if campaign can be started (not paused)."""
```

---

### Step 4: Integrate Campaign Pausing with Circuit Breaker

**Goal**: Automatically pause campaigns when circuit breakers open for required services.

**Actions**:
1. Update `CircuitBreakerService` to trigger campaign pausing
2. Modify `QueueManager` to handle both job and campaign pausing
3. Add service-to-campaign dependency mapping
4. Implement automatic campaign resumption when services recover
5. Add comprehensive logging and alerting for campaign state changes

**Verification Strategy**:
- Simulate circuit breaker opening and verify campaigns are paused
- Test service recovery and automatic campaign resumption
- Verify only dependent campaigns are affected
- Check that alerts and logs are generated appropriately

**Implementation Details**:
```python
# Update app/core/circuit_breaker.py
def _pause_service_queues(self, service: ThirdPartyService):
    """Pause queues and campaigns related to a service."""
    # Existing job pausing logic
    # Add campaign pausing logic
    
# Update app/core/queue_manager.py  
def pause_campaigns_for_service(self, service: ThirdPartyService, reason: str) -> int:
    """Pause campaigns that depend on a service."""
```

---

### Step 5: Update API Endpoints for Campaign Pausing

**Goal**: Expose campaign pausing functionality through REST API endpoints.

**Actions**:
1. Add campaign pause/resume endpoints to campaigns router
2. Update queue management endpoints to include campaign status
3. Add bulk campaign operations for service-based pausing
4. Implement proper error handling and validation
5. Add OpenAPI documentation for new endpoints

**Verification Strategy**:
- Test all new endpoints with various scenarios
- Verify proper HTTP status codes and error messages
- Test endpoint authorization and validation
- Confirm API documentation is generated correctly

**Implementation Details**:
```python
# In app/api/endpoints/campaigns.py
@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str, reason: PauseRequest, db: Session):
    """Pause a specific campaign."""

@router.post("/{campaign_id}/resume") 
async def resume_campaign(campaign_id: str, db: Session):
    """Resume a paused campaign."""

# In app/api/endpoints/queue_management.py
@router.get("/campaign-status")
async def get_campaign_pause_status():
    """Get pause status for all campaigns."""
```

---

### Step 6: Implement Business Rule Enforcement

**Goal**: Enforce the rule that paused campaigns cannot be started.

**Actions**:
1. Update campaign start validation in `CampaignService`
2. Add pre-start circuit breaker checks
3. Implement queue pause detection before campaign start
4. Update campaign creation to check global pause state
5. Add appropriate error messages and user feedback

**Verification Strategy**:
- Test starting campaigns when services are paused
- Verify appropriate error messages are returned
- Test campaign creation during service outages
- Confirm paused campaigns cannot transition to running

**Implementation Details**:
```python
# In app/services/campaign.py
async def start_campaign(self, campaign_id: str, start_data: CampaignStart, db: Session) -> Dict[str, Any]:
    """Start a campaign with circuit breaker and pause checks."""
    # Check if any required services are paused
    # Prevent starting if dependencies are unavailable
    # Return clear error messages
```

---

### Step 7: Create Comprehensive Test Suite

**Goal**: Ensure all pausing functionality is thoroughly tested at the API level.

**Actions**:
1. Create campaign pausing API tests in `tests/test_campaigns_api.py`
2. Add circuit breaker integration tests for campaign pausing
3. Create queue management tests for campaign operations
4. Add service dependency testing scenarios
5. Implement database validation tests for paused states

**Verification Strategy**:
- Run all existing tests to ensure no regressions
- Execute new tests individually to verify functionality
- Run full test suite to confirm integration
- Test edge cases and error conditions

**Test Scenarios**:
```python
# Key test scenarios to implement:
- test_pause_running_campaign_success()
- test_resume_paused_campaign_success()  
- test_cannot_start_paused_campaign()
- test_circuit_breaker_pauses_campaigns()
- test_service_recovery_resumes_campaigns()
- test_bulk_campaign_pausing_by_service()
- test_campaign_pause_status_endpoints()
- test_campaign_pausing_with_concurrent_jobs()
```

---

### Step 8: Database Migration and Data Integrity

**Goal**: Ensure database schema supports all pausing functionality with data integrity.

**Actions**:
1. Create migration for CampaignStatus enum update
2. Add database constraints and indexes for performance
3. Handle existing data migration gracefully
4. Add database functions for bulk operations if needed
5. Verify foreign key constraints work with new statuses

**Verification Strategy**:
- Run migrations in test environment first
- Verify all existing data remains valid
- Test rollback scenarios
- Check database performance with new indexes

**Migration Tasks**:
```sql
-- Add paused to campaignstatus enum
-- Update any existing campaign data if needed
-- Add indexes for status-based queries
-- Verify enum consistency across tables
```

---

### Step 9: Integration Testing and Performance Verification

**Goal**: Verify the complete system works under realistic load and failure scenarios.

**Actions**:
1. Create integration tests that simulate realistic circuit breaker scenarios
2. Test campaign pausing under concurrent load
3. Verify performance impact of new pausing logic
4. Test recovery scenarios with multiple campaigns
5. Add monitoring and alerting validation

**Verification Strategy**:
- Run load tests with campaign pausing enabled
- Simulate various failure and recovery scenarios
- Monitor database performance under pause/resume operations
- Verify alerting systems work correctly

**Performance Tests**:
```python
# Integration test scenarios:
- test_concurrent_campaign_pausing_performance()
- test_bulk_pause_resume_operations()
- test_circuit_breaker_recovery_timing()
- test_campaign_state_consistency_under_load()
```

---

### Step 10: Documentation and Deployment Preparation

**Goal**: Document the new functionality and prepare for deployment.

**Actions**:
1. Update API documentation with new endpoints and behavior
2. Create operational runbooks for campaign pausing scenarios
3. Update monitoring and alerting documentation
4. Create deployment notes for production rollout
5. Update user-facing documentation about campaign states

**Verification Strategy**:
- Review documentation for completeness and accuracy
- Test documented procedures in staging environment
- Verify monitoring dashboards show new metrics
- Confirm rollback procedures are documented

**Documentation Updates**:
- API specification updates for new endpoints
- Circuit breaker behavior documentation
- Campaign lifecycle documentation
- Troubleshooting guides for paused states
- Deployment and rollback procedures

## Implementation Order and Dependencies

### Phase 1: Foundation (Steps 1-2)
- **Priority**: Critical - Fix enum case mismatch first
- **Dependencies**: None - can be implemented immediately
- **Risk**: High - Current system has broken job pausing

### Phase 2: Core Logic (Steps 3-4)  
- **Priority**: High - Core pausing functionality
- **Dependencies**: Phase 1 must be complete
- **Risk**: Medium - Requires careful state management

### Phase 3: API Integration (Steps 5-6)
- **Priority**: High - User-facing functionality 
- **Dependencies**: Phase 2 complete
- **Risk**: Low - Standard API development

### Phase 4: Quality Assurance (Steps 7-9)
- **Priority**: High - Ensure reliability
- **Dependencies**: Phase 3 complete  
- **Risk**: Medium - Complex testing scenarios

### Phase 5: Production Readiness (Step 10)
- **Priority**: Medium - Operational support
- **Dependencies**: All previous phases
- **Risk**: Low - Documentation and procedures

## Risk Mitigation Strategies

### High-Risk Areas
1. **Database Enum Consistency**: Ensure all enum values match between code and database
2. **State Transition Integrity**: Verify campaign state transitions don't create invalid states
3. **Concurrent Access**: Handle race conditions during pause/resume operations
4. **Performance Impact**: Monitor database performance with new status queries

### Rollback Planning
1. **Migration Rollbacks**: Prepare reverse migrations for all database changes
2. **Feature Flags**: Consider implementing feature flags for gradual rollout
3. **Data Recovery**: Ensure paused campaigns can be manually recovered if needed
4. **Service Isolation**: Design so circuit breaker issues don't cascade

## Success Criteria

### Functional Requirements Met
- [ ] Jobs can be successfully paused when circuit breakers open
- [ ] Campaigns can be paused and resumed correctly
- [ ] Paused campaigns cannot be started
- [ ] Circuit breaker integration automatically pauses dependent campaigns
- [ ] All API endpoints function correctly
- [ ] Database maintains data integrity

### Technical Requirements Met  
- [ ] All existing tests continue to pass
- [ ] New functionality has comprehensive test coverage
- [ ] Performance impact is within acceptable limits
- [ ] Documentation is complete and accurate
- [ ] Monitoring and alerting work correctly
- [ ] Rollback procedures are tested and documented

### Operational Requirements Met
- [ ] Support team has operational runbooks
- [ ] Monitoring dashboards include new metrics
- [ ] Alerting is configured for campaign state changes
- [ ] Deployment procedures are documented and tested

## Conclusion

This implementation plan provides a comprehensive, step-by-step approach to adding graceful circuit breaker pausing functionality. The plan prioritizes fixing the critical enum case mismatch first, then builds upon the existing architecture to add campaign pausing capabilities while maintaining system integrity and performance.

The implementation follows established patterns in the codebase, includes comprehensive testing, and provides operational support for production deployment. Each step includes clear verification strategies and builds upon previous steps to ensure a reliable implementation. 