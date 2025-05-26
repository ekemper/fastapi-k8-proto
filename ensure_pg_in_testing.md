# Ensuring API Functional Tests Use Postgres in Docker for fastapi-k8-proto

## Overview
This document provides a comprehensive, step-by-step guide for an AI agent to review and ensure that all API functional tests in the `fastapi-k8-proto` project run against a PostgreSQL database hosted in the API Docker container. The process strictly maintains existing project conventions and patterns. Unit tests are excluded; the focus is on functional API tests that interact with the API and verify results in the database.

---

## Step 1: Confirm Dockerized Postgres Setup
**Goal:** Ensure the API Docker container runs a Postgres instance accessible to the app and tests.

**Actions:**
- Inspect Docker Compose or Dockerfile for Postgres service/container.
- Confirm environment variables for Postgres (host, port, user, password, db name) are set and used by the app.
- Check that the API container can connect to Postgres using these variables.

**Verification:**
- Run `docker compose ps` (or equivalent) to confirm Postgres is running.
- `docker compose exec <api-container> psql -h <pg-host> -U <pg-user> <db>` to confirm connectivity.

---

## Step 2: Review Test Database Configuration
**Goal:** Ensure all test configuration points to the Dockerized Postgres, not SQLite or any other DB.

**Actions:**
- Search for test database URLs in config files, fixtures, and test setup scripts.
- Confirm all use a Postgres URL (e.g., `postgresql://...`).
- Remove or update any SQLite references.

**Verification:**
- Grep for `sqlite` and confirm no matches in config, fixtures, or test code.
- Grep for `postgresql` and confirm correct usage in test configs.

---

## Step 3: Validate API Functional Test Patterns
**Goal:** Ensure all functional tests hit the API endpoints and verify DB state.

**Actions:**
- Review test files (typically in `tests/` or `tests/api/`) for usage of HTTP clients (e.g., `TestClient`, `httpx`, `requests`).
- Confirm tests make real HTTP requests to the running API (not direct function calls).
- Check that tests verify results by querying the Postgres DB (using SQLAlchemy or raw SQL).

**Verification:**
- Identify at least one test per endpoint that:
  - Sends an HTTP request to the API.
  - Verifies the response.
  - Queries the DB to confirm the expected state.

---

## Step 4: Ensure Test Isolation and Cleanup
**Goal:** Guarantee each test runs in isolation and cleans up DB state.

**Actions:**
- Check for setup/teardown or fixture logic that resets the DB between tests (e.g., truncates tables, rolls back transactions, or uses test schemas).
- Confirm this logic works with Postgres in Docker.

**Verification:**
- Run the full test suite multiple times in a row; results should be consistent and not depend on previous runs.
- No leftover data should persist between tests.

---

## Step 5: Confirm Migrations Are Applied in Test Environment
**Goal:** Ensure the test Postgres DB schema matches the latest migrations.

**Actions:**
- Check test setup scripts or CI config for migration commands (e.g., `alembic upgrade head`).
- Ensure these commands run inside the API Docker container before tests start.

**Verification:**
- Run `alembic current` in the API container and confirm the schema is up to date.
- Tests should not fail due to missing columns/tables.

---

## Step 6: Run Functional API Tests Against Dockerized Postgres
**Goal:** Execute the functional API tests using the Dockerized Postgres and verify all pass.

**Actions:**
- Start the full Docker environment (`docker compose up -d`).
- Run the test suite (e.g., `pytest tests/` or via Makefile/script) from within the API container or with env vars pointing to Dockerized Postgres.

**Verification:**
- All tests pass.
- Parse test output for errors or DB connection issues.

---

## Step 7: Manual API/DB Verification (Optional)
**Goal:** Spot-check API and DB integration manually.

**Actions:**
- Use `curl` or `http` to hit an API endpoint.
- Connect to the Postgres DB in the container and check for expected data.

**Verification:**
- Data created/modified by the API is present in the DB as expected.

---

## Step 8: Document and Commit Changes
**Goal:** Ensure all changes and findings are documented and versioned.

**Actions:**
- Update this document with any project-specific notes or deviations.
- Commit all code/config changes and this markdown file to version control.

**Verification:**
- `git status` is clean after commit.

---

## Notes
- All code/config edits should be performed by the AI agent.
- All commands should be run in the chat context, with output parsed for actionable info.
- Migrations must be run inside the API Docker container.
- Only functional API tests are in scope (no unit tests).
- Always maintain existing project conventions and patterns. 