# Plan to Fix Functional API Test Fixture and Isolation Issues

## Overview
This document provides a detailed, step-by-step plan to repair the test fixture setup and ensure reliable, isolated, and Postgres-backed functional API tests for the `fastapi-k8-proto` project. Each step includes a clear goal, actions for the AI agent, and a verification strategy.

---

## Step 1: Audit and Repair `db_session` and Related Fixtures
**Goal:** Ensure `db_session` and all related fixtures are always available and correctly injected in every test context.

**Actions:**
- Review `conftest.py` for fixture definitions and scope.
- Check all test files for correct usage of `db_session`, `client`, and related fixtures.
- Refactor fixtures to:
  - Always yield a valid SQLAlchemy session.
  - Properly override FastAPI's `get_db` dependency for all tests.
  - Use function scope for isolation.
- Remove or fix any code that sets `db_session = None` or fails to yield a session.

**Verification:**
- All test files can access a working `db_session` and `client` fixture.
- No test fails with `db_session = None` or `AttributeError: 'NoneType' object has no attribute 'query'`.

---

## Step 2: Ensure All Test Files Import and Use Correct Fixtures
**Goal:** Guarantee every test file uses the shared fixtures from `conftest.py` and does not define conflicting or broken local fixtures.

**Actions:**
- Audit all test files for local fixture definitions that shadow or conflict with those in `conftest.py`.
- Remove or update local fixtures to import from `conftest.py`.
- Ensure all tests use the shared `db_session`, `client`, and related fixtures.

**Verification:**
- No duplicate/conflicting fixture definitions in test files.
- All tests use the correct, working fixtures from `conftest.py`.

---

## Step 3: Fix Test Data Setup for Parent/Child Relationships
**Goal:** Ensure all tests create required parent data (e.g., organizations) before creating dependent records (e.g., campaigns).

**Actions:**
- Review all tests that create child records with foreign keys.
- Add setup steps to create parent records in the database before creating children.
- Use helper functions or fixtures to streamline parent data creation.

**Verification:**
- No test fails with `IntegrityError: ... violates foreign key constraint`.
- All parent/child data relationships are valid in test DB state.

---

## Step 4: Re-run the Full Test Suite and Verify Isolation
**Goal:** Confirm all tests pass consistently and DB state is clean between tests.

**Actions:**
- Run the full test suite in the Docker test environment (e.g., `docker compose -f docker/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner`).
- Repeat the test run multiple times to check for data leakage or inconsistent results.
- Review test output for errors, warnings, or leftover data.

**Verification:**
- All tests pass on repeated runs.
- No data persists between tests; each test starts with a clean DB state.

---

## Step 5: Document and Commit All Changes
**Goal:** Ensure all fixture, test, and documentation changes are tracked and versioned.

**Actions:**
- Update this README with any project-specific notes or deviations.
- Commit all code and documentation changes to version control.

**Verification:**
- `git status` is clean after commit.

---

## Notes
- Maintain all existing project conventions and patterns.
- Only functional API tests are in scope (no unit tests).
- All code edits and commands should be performed by the AI agent as described. 