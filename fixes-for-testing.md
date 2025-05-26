# Comprehensive Review & Repair Instructions for API Functional Testing (Postgres, Docker)

## Overview
This document provides a granular, step-by-step guide for an AI agent to review, repair, and verify that all API functional tests in the `fastapi-k8-proto` project run against a PostgreSQL database hosted in the API Docker container. All project conventions and patterns must be strictly maintained. Each step includes a clear goal, actionable tasks, and a robust verification strategy.

---

## Step 1: Confirm Dockerized Postgres Environment for API Tests
**Goal:** Ensure all API functional tests run against a Postgres DB in the Docker container, not SQLite or any local DB.

**Actions:**
- Inspect `docker/docker-compose.yml` and `docker/docker-compose.test.yml` for Postgres service and test-runner configuration.
- Check test DB connection strings in environment files and test settings (should reference Postgres, not SQLite).
- Verify that the test runner service depends on the Postgres service.

**Verification:**
- Run `docker compose -f docker/docker-compose.test.yml ps` and confirm Postgres and test-runner containers are up.
- Check logs for Postgres startup and test-runner DB connection.
- Confirm no SQLite files or references exist in the codebase.

---

## Step 2: Audit Test Database URL Usage
**Goal:** Ensure all test code, fixtures, and helpers use the Postgres DB URL from Docker, not any local or SQLite DB.

**Actions:**
- Search for all DB URL usages in test config, fixtures, and helpers.
- Remove or update any SQLite or local DB URLs to use the Docker Postgres URL.
- Ensure test DB URL is injected via environment variables or config files.

**Verification:**
- Grep for `sqlite` and confirm zero matches in Python and YAML files.
- Grep for `postgresql` and confirm all test DB URLs are correct.

---

## Step 3: Confirm API Tests Hit Real Endpoints and Check DB State
**Goal:** Ensure all functional API tests use HTTP clients (e.g., TestClient, httpx) to hit API endpoints and verify DB state post-request.

**Actions:**
- Audit all test files for usage of HTTP clients to interact with API endpoints.
- Ensure tests do not directly manipulate DB except for setup/teardown.
- Confirm tests check DB state after API calls (e.g., querying for created/updated rows).

**Verification:**
- Spot-check test files for API calls and DB assertions.
- Run a sample test and confirm it fails if the DB is not updated as expected.

---

## Step 4: Audit and Repair Test Fixtures for DB Session and Data Isolation
**Goal:** Ensure all tests use shared, properly scoped DB session fixtures and that test data is isolated between tests.

**Actions:**
- Review `conftest.py` and all test files for DB session fixture usage.
- Remove local/duplicate DB session fixtures; use shared fixture from `conftest.py`.
- Ensure all test data setup/teardown is handled via fixtures.
- Confirm that each test starts with a clean DB state (truncate or rollback between tests).

**Verification:**
- Run the full test suite twice in a row; results should be identical and independent.
- Check for data leakage by querying the DB after test runs.

---

## Step 5: Ensure All Foreign Key and Required Fields Are Satisfied in Test Data
**Goal:** Prevent NOT NULL and FK constraint errors by ensuring all required fields and relationships are set in test data.

**Actions:**
- Audit all test and fixture code that creates DB objects (e.g., Campaign, Job, Organization).
- Update test data to provide all required fields (e.g., `name`, `description` for Job).
- Ensure all FKs (e.g., `organization_id` for Campaign, `campaign_id` for Job) reference real, persisted parent objects.
- For fixtures that create multiple objects, ensure variety where required (e.g., multiple organizations for campaign tests).

**Verification:**
- Run the test suite and confirm no NOT NULL or FK constraint errors.
- Spot-check DB tables after test runs for valid, complete rows.

---

## Step 6: Standardize Datetime Usage in Tests and Fixtures
**Goal:** Prevent offset-naive/aware datetime errors in test logic.

**Actions:**
- Audit all datetime usage in test and fixture code.
- Standardize to use either all UTC-aware or all naive datetimes (prefer UTC-aware: `datetime.utcnow().replace(tzinfo=timezone.utc)`).
- Update any code that mixes naive and aware datetimes.

**Verification:**
- Run tests that compare or subtract datetimes; confirm no TypeError is raised.

---

## Step 7: Refactor Concurrent and Threaded Tests for Session Safety
**Goal:** Ensure concurrent tests use thread-local DB sessions and clients to avoid transaction state errors.

**Actions:**
- Audit all tests using threading or concurrency.
- Refactor to create a new DB session and API client per thread.
- Avoid sharing session or client objects across threads.

**Verification:**
- Run all concurrent tests; confirm no transaction or session state errors.

---

## Step 8: Remove Stale Imports and Undefined Symbols
**Goal:** Eliminate NameError, ImportError, and AttributeError from test code.

**Actions:**
- Audit all test files for imports of undefined or removed symbols (e.g., `TestingSessionLocal`).
- Remove or update all such imports and usages.
- Ensure all fixtures and helpers are imported from their correct, current locations.

**Verification:**
- Run the test suite and confirm no import or name errors.

---

## Step 9: Address Deprecation Warnings
**Goal:** Future-proof the codebase by resolving all deprecation warnings.

**Actions:**
- Update Pydantic configs to use `ConfigDict` instead of class-based `config`.
- Update SQLAlchemy to use `sqlalchemy.orm.declarative_base()`.
- Fix any other deprecation warnings in test output.

**Verification:**
- Run the test suite and confirm no deprecation warnings are emitted.

---

## Step 10: Final Verification
**Goal:** Ensure all API functional tests pass, are isolated, and run against Dockerized Postgres.

**Actions:**
- Run the full test suite using Docker Compose.
- Parse output for errors, warnings, and failed tests.
- Curl a sample API endpoint and check the DB for expected results.

**Verification:**
- All tests pass with no errors or warnings.
- Manual curl/API call results in correct DB changes.
- DB is clean and consistent after test runs.

---

**Note:** For any code edits, perform the changes directly. For commands, run them in the chat window context and parse the output for actionable information. For migrations, always run commands inside the API Docker container. 