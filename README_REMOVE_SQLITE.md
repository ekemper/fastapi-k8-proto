# Removing SQLite from the Codebase: Step-by-Step Guide

This guide outlines the process for completely removing SQLite from the testing and application codebase, ensuring only PostgreSQL is used for all environments.

---

## Step 1: Remove SQLite Usage from All Test Files

**Goal:**  
No test file should reference or use SQLite. All tests should use PostgreSQL via environment variables and the shared test configuration.

**Actions:**
- Search for all references to `sqlite` and `create_engine(...sqlite...)` in `tests/`.
- Remove or refactor any test-specific database setup to use the shared `db_session`/`client` fixtures from `conftest.py`.
- Remove any SQLite-specific test database files from the repo (e.g., `test.db`, `test_helpers.db`, etc.).

**Confirmation:**
- Grep for `sqlite` in the codebase. There should be zero matches in `.py` files.
- All test files should import and use only the shared fixtures.

---

## Step 2: Remove SQLite from Application Code

**Goal:**  
The application should not support or reference SQLite in any configuration, code, or documentation.

**Actions:**
- Search for `sqlite` in `app/`, `alembic/`, and config files.
- Remove any SQLite fallback logic in `app/core/config.py` or similar.
- Ensure `DATABASE_URL` and all DB connection logic only support PostgreSQL.

**Confirmation:**
- Grep for `sqlite` in the codebase. There should be zero matches in `.py` or config files.
- The app should fail to start if a non-PostgreSQL URL is provided.

---

## Step 3: Remove SQLite from Requirements and Dependencies

**Goal:**  
No SQLite-related packages should be installed or referenced.

**Actions:**
- Remove `pysqlite3`, `sqlite3`, or similar from all `requirements/*.txt` files.
- Remove any SQLite-related dev dependencies.

**Confirmation:**
- Grep for `sqlite` in all requirements files. There should be zero matches.

---

## Step 4: Remove SQLite Test Artifacts and Files

**Goal:**  
No SQLite database files or related artifacts should remain in the repo.

**Actions:**
- Delete all `.db` files in the root and `tests/` directories.
- Add a `.gitignore` rule for `*.db` if not already present.

**Confirmation:**
- `ls *.db` and `ls tests/*.db` should return no files.
- `.gitignore` should include `*.db`.

---

## Step 5: Update Documentation and Developer Instructions

**Goal:**  
All documentation should reference only PostgreSQL for development and testing.

**Actions:**
- Update `README.md`, `CONTRIBUTING.md`, and any setup docs to remove SQLite references.
- Ensure all setup instructions use PostgreSQL.

**Confirmation:**
- Grep for `sqlite` in all documentation. There should be zero matches.

---

## Step 6: Run All Tests in Docker Compose Test Environment

**Goal:**  
All tests should pass using only PostgreSQL, confirming no hidden SQLite dependencies.

**Actions:**
- Run:
  ```sh
  docker-compose -f docker/docker-compose.test.yml run --rm test-runner
  ```
- Parse output for errors related to database connections or missing dependencies.

**Confirmation:**
- All tests pass or only fail for reasons unrelated to database backend.
- No errors about missing SQLite or fallback to SQLite.

---

## Step 7: Remove SQLite from Alembic and Migration Scripts

**Goal:**  
Alembic and migration scripts should not reference SQLite.

**Actions:**
- Check `alembic.ini`, `alembic/env.py`, and migration scripts for SQLite logic.
- Remove any SQLite-specific code or comments.

**Confirmation:**
- Grep for `sqlite` in `alembic/`. There should be zero matches.

---

**Follow these steps to ensure a clean, PostgreSQL-only codebase and test environment.** 