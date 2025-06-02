# Reset and Run Concurrent Campaigns Test Plan

## Executive Summary

This document outlines a comprehensive plan to create a shell script (`reset_and_run_concurrent_campaigns_test.sh`) that will reset the application state and run the concurrent campaigns flow test. The script will provide a clean, repeatable testing environment for validating the application's concurrent processing capabilities.

## Architecture Assessment

### Current Application Structure
- **FastAPI backend** with Celery workers for background processing
- **PostgreSQL** database with tables: jobs, leads, campaigns, organizations, users
- **Redis** for caching and Celery message broker
- **Docker Compose** setup with services: api, worker (8 replicas), postgres, redis, flower, frontend
- **Alembic** for database migrations
- **Pytest** for testing framework

### Current Patterns and Conventions
- Uses `docker compose` (not deprecated `docker-compose`)
- Container names follow pattern: `fastapi-k8-proto-{service}-{replica}`
- API container: `fastapi-k8-proto-api-1`
- Database operations should be executed within API container
- Tests run within API container context
- Logs are shared via volume mount: `./logs:/app/logs`

### Test Target Analysis
- **Test File**: `app/background_services/smoke_tests/test_concurrent_campaigns_flow.py`
- **Purpose**: Tests concurrent processing of 10 campaigns with 20 leads each
- **Process Flow**: Campaign creation → Lead fetching → Concurrent enrichment jobs
- **Dependencies**: Mock Apify client, database, Redis, authentication system

## Implementation Plan

### Phase 1: Environment Assessment and Validation
**Goal**: Verify current environment state and validate assumptions

**Actions**:
1. Check Docker container status and names
2. Verify database connectivity within API container
3. Verify Redis connectivity within API container
4. Validate log file location and permissions
5. Confirm test file exists and is executable

**Success Criteria**:
- All expected containers are running
- Database connection successful from API container
- Redis connection successful from API container
- Log file is accessible and writable
- Test file exists at expected location

### Phase 2: Log File Management
**Goal**: Clean the shared log file to start with fresh logs

**Actions**:
1. Truncate `./logs/combined.log` file
2. Verify truncation was successful
3. Ensure proper permissions are maintained

**Success Criteria**:
- Log file exists but is empty (0 bytes)
- File permissions allow container write access

### Phase 3: Container Restart
**Goal**: Restart all containers to ensure clean state

**Actions**:
1. Use `docker compose restart` to restart all services
2. Wait for health checks to pass
3. Verify all services are running and healthy

**Success Criteria**:
- All containers restart successfully
- Health checks pass for postgres and redis
- API service is accessible

### Phase 4: Database Table Truncation
**Goal**: Clear specific database tables to ensure clean test state

**Actions**:
1. Execute within API container using `docker exec`
2. Connect to PostgreSQL database
3. Truncate tables in correct order (respecting foreign key constraints):
   - jobs (has FK to campaigns)
   - leads (has FK to campaigns and organizations)
   - campaigns (has FK to organizations and users)
   - organizations (has FK to users)
4. Verify truncation was successful

**SQL Execution Order**:
```sql
TRUNCATE TABLE jobs CASCADE;
TRUNCATE TABLE leads CASCADE;  
TRUNCATE TABLE campaigns CASCADE;
TRUNCATE TABLE organizations CASCADE;
```

**Success Criteria**:
- All specified tables are empty
- No foreign key constraint violations
- Database remains in consistent state

### Phase 5: Redis Cache Clearing
**Goal**: Clear Redis cache to ensure clean state

**Actions**:
1. Execute within API container using `docker exec`
2. Connect to Redis
3. Execute `FLUSHALL` command to clear all keys
4. Verify cache is cleared

**Success Criteria**:
- Redis returns confirmation of flush operation
- All keys are removed from Redis

### Phase 6: Test Execution
**Goal**: Run the concurrent campaigns flow test

**Actions**:
1. Execute test within API container using `docker exec`
2. Run `python app/background_services/smoke_tests/test_concurrent_campaigns_flow.py`
3. Monitor test progress through logs
4. Capture test results and any errors

**Success Criteria**:
- Test starts successfully
- All 10 campaigns are created
- Concurrent processing completes without errors
- Test passes all assertions

### Phase 7: Results Validation
**Goal**: Verify test completion and validate results

**Actions**:
1. Check test exit code
2. Review log output for errors
3. Validate database state post-test
4. Confirm expected number of jobs and leads were created

**Success Criteria**:
- Test exits with code 0 (success)
- No critical errors in logs
- Database contains expected test data
- All concurrent jobs completed successfully

## Implementation Rules and Guidelines

### General Rules
1. **Always make a technical, critical assessment** for any queries, statements, ideas, questions
2. **Ask for clarification** when needed from the user during implementation
3. **NEVER MAKE ASSUMPTIONS** - always provide rationale for decisions
4. **Perform code edits** when required for implementation
5. **Run commands** in chat window context and parse output for errors
6. **Create and run migrations** in the API docker container
7. **Pay attention to API testing logic** (routes, service, model, tests)
8. **Run tests after making changes** to the API
9. **Run individual tests** in API docker container: `docker exec fastapi-k8-proto-api-1 pytest...`
10. **Run full test suite** using `make docker-test`
11. **Assess environment variables** using `cat .env`
12. **DO NOT modify env files**
13. **Run database/redis commands** in API docker container
14. **Check container names** with `docker ps` before using
15. **Use newer `docker compose`** command version, not deprecated `docker-compose`

### Error Handling Strategy
- Graceful failure with clear error messages
- Rollback capability if partial execution fails
- Detailed logging of each step
- Exit codes that indicate specific failure points

### Testing Strategy
- Each phase has clear success criteria
- Incremental validation at each step
- Ability to resume from specific phase if needed
- Comprehensive logging for debugging

## Script Structure

### File: `reset_and_run_concurrent_campaigns_test.sh`
```bash
#!/bin/bash
# Reset and Run Concurrent Campaigns Test
# 
# This script performs a complete reset of the application state
# and runs the concurrent campaigns flow test
#
# Usage: ./reset_and_run_concurrent_campaigns_test.sh
```

### Key Features
- **Executable permissions** set automatically
- **Error handling** with trap functions
- **Colored output** for better visibility
- **Step-by-step progress** indicators
- **Detailed logging** of all operations
- **Exit codes** for specific failure types

### Prerequisites Validation
- Docker and Docker Compose installed
- Current directory is project root
- All required containers are buildable
- User has necessary permissions

## Risk Assessment

### High Risk Items
1. **Database truncation** - Risk of data loss if run in production
2. **Container restart** - May affect other development work
3. **Foreign key constraints** - Could cause database inconsistency

### Mitigation Strategies
1. **Environment detection** - Warn if production-like environment detected
2. **Confirmation prompts** - Ask user to confirm destructive operations
3. **Backup recommendations** - Suggest database backup before running
4. **Rollback procedures** - Document how to restore previous state

## Success Metrics

### Quantitative Metrics
- Script execution time < 5 minutes
- 100% of database tables truncated successfully
- 10 campaigns created in test
- 200 leads processed (20 per campaign)
- 200 enrichment jobs completed successfully

### Qualitative Metrics
- Clean log output with no errors
- Predictable and repeatable execution
- Clear progress indicators
- Comprehensive error reporting

## Future Enhancements

1. **Configuration options** - Allow customization of test parameters
2. **Selective reset** - Option to reset only specific components
3. **Test variants** - Support for different test scenarios
4. **Performance monitoring** - Track execution times and resource usage
5. **Integration with CI/CD** - Make script suitable for automation

## Documentation Requirements

- **Usage instructions** in script header
- **Error codes** documented with meanings
- **Dependencies** clearly listed
- **Troubleshooting guide** for common issues
- **Update this plan** when implementation reveals new patterns or issues

---

**Document Version**: 1.0  
**Created**: Current Date  
**Author**: AI Assistant  
**Status**: Implementation Ready 