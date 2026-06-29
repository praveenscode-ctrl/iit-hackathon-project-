# AssignHub — Phase 1 to Phase 3 Full Verification & Unit Test Suite
**Purpose:** Single source of truth for verifying every checkpoint across Phase 1 (Foundation), Phase 2 (Auth), and Phase 3 (Classes & Provisioning).  
**Who runs this:** Developer after completing each phase — run in order, never skip.  
**Rule:** Every checkpoint must show PASS before moving to the next phase.

---

## How to Use This File

1. Complete the phase implementation
2. Run every checkpoint in that phase section top to bottom
3. Each checkpoint has: manual curl test + SQL verification + unit test reference
4. If any checkpoint fails: fix the bug, re-run that checkpoint, then continue
5. Do not proceed to the next phase until the current phase shows all PASS

---

## Pre-flight: Test Environment Setup

Run once before any phase verification:

```bash
# From Backend/ directory
pip install pytest pytest-asyncio httpx

# Create test DB (separate from dev DB — avoids polluting real data)
# In PostgreSQL:
CREATE DATABASE assignhub_test;

# Set test env — create a .env.test file
cp .env .env.test
# Edit .env.test: change DATABASE_URL to point to assignhub_test
```

Create `Backend/conftest.py` — used by all unit tests:

```python
# Backend/conftest.py

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv(".env.test")

from database import Base, get_db
from main import app

TEST_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Fresh DB session per test. Rolls back after each test."""
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db):
    """Test client with DB override."""
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def admin_token(client):
    """Creates admin account and returns valid access token."""
    client.post("/api/v1/auth/admin/signup", json={
        "full_name": "Test Admin",
        "email": "admin@test.com",
        "password": "Test1234!"
    })
    from models.user import OtpVerification
    from database import SessionLocal
    db = SessionLocal()
    otp_row = db.query(OtpVerification).filter_by(email="admin@test.com").first()
    otp_code = otp_row.otp_code
    db.close()
    resp = client.post("/api/v1/auth/admin/verify-otp", json={
        "email": "admin@test.com",
        "otp": otp_code
    })
    return resp.json()["access_token"]

@pytest.fixture(scope="function")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
```

---

## PHASE 1 — Foundation Verification

### Manual Checkpoints

---

#### CP-1.1 — Server starts without errors

```bash
cd Backend
uvicorn main:app --reload
```

**What to check:**
- Terminal shows `Uvicorn running on http://127.0.0.1:8000`
- Zero import errors
- Zero `ModuleNotFoundError`
- Scheduler starts: look for APScheduler log line

**PASS condition:** Server is running and accepting connections.

---

#### CP-1.2 — Health endpoint responds correctly

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

**Expected response:**
```json
{
    "status": "ok",
    "timestamp": "2026-06-25T10:00:00.000000Z"
}
```

**What to check:**
- HTTP status: 200
- `status` is exactly `"ok"` — not `"OK"`, not `"healthy"`, not `"running"`
- `timestamp` is a valid ISO 8601 string ending in `Z`

**PASS condition:** Both fields correct.

---

#### CP-1.3 — Alembic migration runs cleanly

```bash
alembic upgrade head
```

**Expected output (no errors):**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001abc, initial_schema
```

**PASS condition:** No error lines. No `FAILED`. No `Table already exists` errors on first run.

---

#### CP-1.4 — All 17 tables exist

```sql
-- Run in psql or any PG client
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
```

**Expected — exactly these 17 table names:**
```
admin_profiles
ai_query_logs
assignment_analytics
assignments
bulk_import_batches
bulk_import_errors
class_analytics
class_memberships
classes
export_jobs
notifications
otp_verifications
refresh_tokens
reminder_jobs
student_analytics
submissions
users
```

**PASS condition:** All 17 present. No extras. No missing.

---

#### CP-1.5 — UUID primary keys confirmed

```sql
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'id';
```

**Expected:**
- `data_type` = `uuid`
- `column_default` contains `gen_random_uuid()`

Run same check on `classes`, `assignments`, `submissions`:
```sql
SELECT table_name, column_name, data_type, column_default
FROM information_schema.columns
WHERE column_name = 'id'
AND table_name IN ('users','classes','assignments','submissions','class_memberships','notifications')
ORDER BY table_name;
```

**PASS condition:** All show `uuid` data_type and `gen_random_uuid()` default.

---

#### CP-1.6 — TIMESTAMPTZ on all timestamp columns

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'users' 
AND column_name IN ('created_at', 'updated_at');
```

**Expected:**
- `data_type` = `timestamp with time zone` for both

Also check `submissions.submitted_at`:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'submissions' AND column_name = 'submitted_at';
```

**Expected:** `timestamp with time zone` — NOT `timestamp without time zone`.

**PASS condition:** All timestamp columns show `timestamp with time zone`.

---

#### CP-1.7 — CHECK constraints on users table

```sql
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'users'::regclass AND contype = 'c';
```

**Expected (at minimum these two):**
```
users_role_check    | CHECK (role IN ('ADMIN','MENTOR','STUDENT'))
users_status_check  | CHECK (status IN ('PENDING_OTP','ACTIVE','INACTIVE','BLOCKED'))
```

Also verify `class_memberships` status CHECK includes PENDING:
```sql
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'class_memberships'::regclass AND contype = 'c';
```

**Expected:** Must include `PENDING` and `REJECTED` in the status CHECK:
```
CHECK (status IN ('ACTIVE','INACTIVE','PENDING','REJECTED'))
```

**PASS condition:** Both constraints found with correct values. `PENDING` is in `class_memberships.status` CHECK.

---

#### CP-1.8 — UNIQUE constraint on class_memberships(class_id, user_id)

```sql
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'class_memberships'::regclass AND contype = 'u';
```

**Expected:** A unique constraint on `(class_id, user_id)` exists.

Also check `users.email` unique:
```sql
SELECT conname FROM pg_constraint
WHERE conrelid = 'users'::regclass AND contype = 'u';
```

**Expected:** Constraint on `email` column exists.

**PASS condition:** Both unique constraints found.

---

#### CP-1.9 — Indexes exist

```sql
SELECT indexname, tablename, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname IN (
    'idx_users_email', 'idx_users_role',
    'idx_cm_class', 'idx_cm_user', 'idx_cm_status',
    'idx_assignments_class', 'idx_assignments_status',
    'idx_submissions_assignment', 'idx_submissions_student', 'idx_submissions_current',
    'idx_sa_student', 'idx_sa_class', 'idx_sa_risk',
    'idx_notif_user', 'idx_notif_read',
    'idx_otp_email', 'idx_refresh_user', 'idx_classes_admin'
)
ORDER BY tablename, indexname;
```

**PASS condition:** All 18 indexes found.

---

#### CP-1.10 — Database is empty (no mock data)

```sql
SELECT 
    (SELECT COUNT(*) FROM users) as users,
    (SELECT COUNT(*) FROM classes) as classes,
    (SELECT COUNT(*) FROM assignments) as assignments,
    (SELECT COUNT(*) FROM submissions) as submissions;
```

**Expected:** All counts = 0.

**PASS condition:** All zeros.

---

#### CP-1.11 — Swagger UI loads

Open `http://localhost:8000/docs` in browser.

**What to check:**
- Page loads without 500 error
- Shows `GET /health` as the only route
- No other routes visible (routers not registered yet)

**PASS condition:** Page loads cleanly, only health route shown.

---

### Phase 1 Unit Tests

Create `Backend/tests/test_phase1.py`:

```python
# Backend/tests/test_phase1.py

import pytest
from sqlalchemy import inspect, text
from database import engine, Base


class TestDatabaseTables:
    """Verify all 17 tables exist with correct structure."""

    EXPECTED_TABLES = [
        'users', 'otp_verifications', 'admin_profiles', 'refresh_tokens',
        'classes', 'class_memberships', 'assignments', 'submissions',
        'student_analytics', 'class_analytics', 'assignment_analytics',
        'notifications', 'reminder_jobs', 'bulk_import_batches',
        'bulk_import_errors', 'export_jobs', 'ai_query_logs'
    ]

    def test_all_17_tables_exist(self):
        inspector = inspect(engine)
        existing = inspector.get_table_names()
        for table in self.EXPECTED_TABLES:
            assert table in existing, f"MISSING TABLE: {table}"

    def test_no_extra_tables(self):
        """No unexpected tables (excludes alembic and apscheduler system tables)."""
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
        system_tables = {'alembic_version', 'apscheduler_jobs'}
        app_tables = existing - system_tables
        assert app_tables == set(self.EXPECTED_TABLES), (
            f"Unexpected tables: {app_tables - set(self.EXPECTED_TABLES)}"
        )

    def test_users_table_columns(self):
        inspector = inspect(engine)
        cols = {c['name']: c for c in inspector.get_columns('users')}
        required = ['id', 'role', 'full_name', 'email', 'password_hash',
                    'registration_id', 'phone', 'status', 'fcm_token',
                    'created_at', 'updated_at']
        for col in required:
            assert col in cols, f"MISSING COLUMN users.{col}"

    def test_class_memberships_columns(self):
        inspector = inspect(engine)
        cols = {c['name'] for c in inspector.get_columns('class_memberships')}
        required = ['id', 'class_id', 'user_id', 'member_role', 'is_primary_mentor',
                    'joined_via', 'status', 'rejection_reason', 'created_at', 'updated_at']
        for col in required:
            assert col in cols, f"MISSING COLUMN class_memberships.{col}"

    def test_submissions_has_submitted_at_and_created_at(self):
        inspector = inspect(engine)
        cols = {c['name'] for c in inspector.get_columns('submissions')}
        assert 'submitted_at' in cols, "submissions.submitted_at missing"
        assert 'created_at' in cols, "submissions.created_at missing"
        assert 'is_current' in cols, "submissions.is_current missing"
        assert 'version' in cols, "submissions.version missing"

    def test_student_analytics_uses_numeric_not_interval(self):
        inspector = inspect(engine)
        cols = {c['name']: c for c in inspector.get_columns('student_analytics')}
        assert 'avg_submission_delay_hours' in cols, "avg_submission_delay_hours missing"
        col_type = str(cols['avg_submission_delay_hours']['type']).upper()
        assert 'INTERVAL' not in col_type, (
            "CRITICAL: avg_submission_delay_hours must be NUMERIC, not INTERVAL. "
            "Flutter cannot parse PostgreSQL INTERVAL type."
        )

    def test_class_memberships_status_check_includes_pending(self):
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = 'class_memberships'::regclass AND contype = 'c'
                AND pg_get_constraintdef(oid) ILIKE '%status%'
            """)).fetchone()
        assert result is not None, "No status CHECK on class_memberships"
        constraint_def = result[0]
        assert 'PENDING' in constraint_def, (
            f"CRITICAL: class_memberships.status CHECK must include PENDING. "
            f"Found: {constraint_def}"
        )
        assert 'REJECTED' in constraint_def, (
            f"class_memberships.status CHECK must include REJECTED. Found: {constraint_def}"
        )

    def test_users_status_default_is_active_not_pending(self):
        inspector = inspect(engine)
        cols = {c['name']: c for c in inspector.get_columns('users')}
        default = str(cols['status'].get('default', '')).lower()
        assert 'pending' not in default or 'pending_otp' not in default.replace('pending_otp', ''), (
            "CRITICAL: users.status DEFAULT must not be bare 'PENDING' — "
            "bare 'PENDING' is not in the CHECK constraint and will throw a DB error on every mentor/student INSERT. "
            "Default should be 'ACTIVE'."
        )

    def test_all_pk_are_uuid(self):
        inspector = inspect(engine)
        tables_to_check = ['users', 'classes', 'assignments', 'submissions',
                           'class_memberships', 'notifications', 'student_analytics']
        for table in tables_to_check:
            cols = {c['name']: c for c in inspector.get_columns(table)}
            assert 'id' in cols, f"{table} has no id column"
            col_type = str(cols['id']['type']).upper()
            assert 'UUID' in col_type, f"{table}.id is not UUID type (found: {col_type})"


class TestSecurityUtils:
    """Verify security utility functions."""

    def test_hash_and_verify_password(self):
        from utils.security import hash_password, verify_password
        hashed = hash_password("TestPass123!")
        assert hashed != "TestPass123!"
        assert verify_password("TestPass123!", hashed) is True
        assert verify_password("WrongPass", hashed) is False

    def test_password_hash_is_different_each_time(self):
        from utils.security import hash_password
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2, "bcrypt should produce different hash each time (different salt)"

    def test_make_otp_format(self):
        from utils.security import make_otp
        for _ in range(10):
            otp = make_otp()
            assert len(otp) == 6, f"OTP must be 6 digits, got {len(otp)}"
            assert otp.isdigit(), f"OTP must be all digits, got {otp}"

    def test_make_access_token_payload(self):
        from utils.security import make_access_token, decode_token
        token = make_access_token("test-user-uuid", "ADMIN", None)
        assert isinstance(token, str)
        assert len(token) > 20
        payload = decode_token(token)
        assert payload["sub"] == "test-user-uuid"
        assert payload["role"] == "ADMIN"
        assert payload["class_id"] is None
        assert "exp" in payload

    def test_access_token_with_class_id(self):
        from utils.security import make_access_token, decode_token
        token = make_access_token("student-uuid", "STUDENT", "class-uuid-123")
        payload = decode_token(token)
        assert payload["role"] == "STUDENT"
        assert payload["class_id"] == "class-uuid-123"

    def test_decode_invalid_token_raises(self):
        from utils.security import decode_token
        with pytest.raises(Exception):
            decode_token("this.is.not.a.valid.token")

    def test_hash_and_verify_refresh_token(self):
        from utils.security import hash_refresh_token, verify_refresh_token
        import uuid
        token = str(uuid.uuid4())
        hashed = hash_refresh_token(token)
        assert verify_refresh_token(token, hashed) is True
        assert verify_refresh_token("wrong-token", hashed) is False

    def test_make_mentor_reg_id_format(self):
        from utils.id_generator import make_mentor_reg_id
        for _ in range(5):
            reg_id = make_mentor_reg_id()
            assert reg_id.startswith("MENTOR-"), f"Must start with MENTOR-, got {reg_id}"
            assert len(reg_id) > 7, f"Must have content after MENTOR-, got {reg_id}"


class TestHealthEndpoint:
    """Verify health endpoint behavior."""

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_ok_status(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "ok", f"Expected 'ok', got '{data['status']}'"

    def test_health_returns_timestamp(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)
        assert len(data["timestamp"]) > 10

    def test_health_timestamp_ends_with_z(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["timestamp"].endswith("Z"), (
            f"Timestamp must end with Z for ISO 8601 UTC. Got: {data['timestamp']}"
        )

    def test_health_no_auth_required(self, client):
        """Health must be accessible without any token."""
        resp = client.get("/health")
        assert resp.status_code != 401
        assert resp.status_code != 403
```

**Run Phase 1 tests:**
```bash
cd Backend
pytest tests/test_phase1.py -v
```

**Expected output — all PASSED:**
```
tests/test_phase1.py::TestDatabaseTables::test_all_17_tables_exist PASSED
tests/test_phase1.py::TestDatabaseTables::test_no_extra_tables PASSED
tests/test_phase1.py::TestDatabaseTables::test_users_table_columns PASSED
tests/test_phase1.py::TestDatabaseTables::test_class_memberships_columns PASSED
tests/test_phase1.py::TestDatabaseTables::test_submissions_has_submitted_at_and_created_at PASSED
tests/test_phase1.py::TestDatabaseTables::test_student_analytics_uses_numeric_not_interval PASSED
tests/test_phase1.py::TestDatabaseTables::test_class_memberships_status_check_includes_pending PASSED
tests/test_phase1.py::TestDatabaseTables::test_users_status_default_is_active_not_pending PASSED
tests/test_phase1.py::TestDatabaseTables::test_all_pk_are_uuid PASSED
tests/test_phase1.py::TestSecurityUtils::test_hash_and_verify_password PASSED
tests/test_phase1.py::TestSecurityUtils::test_password_hash_is_different_each_time PASSED
tests/test_phase1.py::TestSecurityUtils::test_make_otp_format PASSED
tests/test_phase1.py::TestSecurityUtils::test_make_access_token_payload PASSED
tests/test_phase1.py::TestSecurityUtils::test_access_token_with_class_id PASSED
tests/test_phase1.py::TestSecurityUtils::test_decode_invalid_token_raises PASSED
tests/test_phase1.py::TestSecurityUtils::test_hash_and_verify_refresh_token PASSED
tests/test_phase1.py::TestSecurityUtils::test_make_mentor_reg_id_format PASSED
tests/test_phase1.py::TestHealthEndpoint::test_health_returns_200 PASSED
tests/test_phase1.py::TestHealthEndpoint::test_health_returns_ok_status PASSED
tests/test_phase1.py::TestHealthEndpoint::test_health_returns_timestamp PASSED
tests/test_phase1.py::TestHealthEndpoint::test_health_timestamp_ends_with_z PASSED
tests/test_phase1.py::TestHealthEndpoint::test_health_no_auth_required PASSED
```

**Phase 1 Gate:** All 22 tests PASS + all 11 manual CPs PASS → proceed to Phase 2.

---

## PHASE 2 — Authentication Verification

### Manual Checkpoints

---

#### CP-2.1 — Admin signup creates user and sends OTP

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/admin/signup \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Test Admin", "email": "admin@test.com", "password": "Test1234!"}' \
  | python3 -m json.tool
```

**Expected response:**
```json
{ "message": "OTP sent to your email" }
```

**DB verification:**
```sql
SELECT id, status, role, registration_id 
FROM users WHERE email='admin@test.com';
```
Expected: `status=PENDING_OTP`, `role=ADMIN`, `registration_id=NULL`

```sql
SELECT otp_code, used, expires_at 
FROM otp_verifications WHERE email='admin@test.com'
ORDER BY created_at DESC LIMIT 1;
```
Expected: `used=false`, `otp_code` is 6 digits, `expires_at` is ~10 minutes from now

**Check Gmail inbox:** OTP email received with 6-digit code.

**PASS condition:** HTTP 201, DB state correct, email received.

---

#### CP-2.2 — Duplicate email returns 409

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/admin/signup \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Duplicate", "email": "admin@test.com", "password": "Test1234!"}' \
  -o /dev/null -w "%{http_code}"
```

**Expected:** `409`

**PASS condition:** HTTP 409 returned.

---

#### CP-2.3 — OTP verify activates admin and returns tokens

*Replace `<OTP>` with the code from Gmail.*

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/admin/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "otp": ""}' \
  | python3 -m json.tool
```

**Expected response shape:**
```json
{
    "access_token": "eyJ...",
    "refresh_token": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "user": {
        "id": "uuid-string",
        "full_name": "Test Admin",
        "role": "ADMIN"
    }
}
```

**DB verification:**
```sql
SELECT status FROM users WHERE email='admin@test.com';
```
Expected: `ACTIVE`

```sql
SELECT COUNT(*) FROM admin_profiles 
WHERE user_id=(SELECT id FROM users WHERE email='admin@test.com');
```
Expected: `1`

```sql
SELECT revoked, expires_at FROM refresh_tokens 
ORDER BY created_at DESC LIMIT 1;
```
Expected: `revoked=false`, `expires_at` ~7 days from now

```sql
SELECT used FROM otp_verifications WHERE email='admin@test.com' ORDER BY created_at DESC LIMIT 1;
```
Expected: `used=true`

**PASS condition:** HTTP 200, all 4 DB checks correct.

---

#### CP-2.4 — Wrong OTP returns 400

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/admin/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "otp": "000000"}' \
  -o /dev/null -w "%{http_code}"
```

**Expected:** `400`

**PASS condition:** HTTP 400.

---

#### CP-2.5 — Expired OTP returns 410

```sql
-- Manually expire the OTP in DB
UPDATE otp_verifications 
SET expires_at = now() - interval '1 minute'
WHERE email='admin2@test.com';
```

First create a second admin to test:
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/admin/signup \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Admin Two", "email": "admin2@test.com", "password": "Test1234!"}'
```

Then expire OTP manually (SQL above), then try to verify:
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/admin/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "admin2@test.com", "otp": ""}' \
  -o /dev/null -w "%{http_code}"
```

**Expected:** `410`

**PASS condition:** HTTP 410.

---

#### CP-2.6 — Admin login returns complete user object

*Use tokens from CP-2.3. Run this after verifying the admin.*

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "Test1234!", "registration_id": "", "fcm_token": ""}' \
  | python3 -m json.tool
```

**Expected — every field must be present:**
```json
{
    "access_token": "eyJ...",
    "refresh_token": "uuid-string",
    "user": {
        "id": "uuid",
        "full_name": "Test Admin",
        "email": "admin@test.com",
        "role": "ADMIN",
        "class_id": null,
        "class_name": null,
        "registration_id": null
    }
}
```

**Critical checks:**
- `class_id` must be `null` — not missing, not empty string
- `class_name` must be `null` — not missing
- `registration_id` must be `null` — not missing

Save the tokens:
```bash
ADMIN_TOKEN=""
ADMIN_REFRESH=""
```

**PASS condition:** HTTP 200, all 7 user fields present with correct types/values.

---

#### CP-2.7 — Wrong password returns 401

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "WrongPassword!", "registration_id": "", "fcm_token": ""}' \
  -o /dev/null -w "%{http_code}"
```

**Expected:** `401`

Also test wrong email:
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "nobody@test.com", "password": "Test1234!", "registration_id": "", "fcm_token": ""}' \
  -o /dev/null -w "%{http_code}"
```

**Expected:** `401`

**PASS condition:** Both return HTTP 401, both return `{"detail": "Invalid credentials"}`.

---

#### CP-2.8 — Token refresh returns new access token

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$ADMIN_REFRESH\"}" \
  | python3 -m json.tool
```

**Expected:**
```json
{ "access_token": "eyJ..." }
```

**What to verify:**
- HTTP 200
- `access_token` is a non-empty JWT string
- The new token is different from the original `ADMIN_TOKEN`

**PASS condition:** HTTP 200, new token returned.

---

#### CP-2.9 — Invalid refresh token returns 401

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "00000000-0000-0000-0000-000000000000"}' \
  -o /dev/null -w "%{http_code}"
```

**Expected:** `401`

**PASS condition:** HTTP 401.

---

#### CP-2.10 — Logout revokes refresh token

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$ADMIN_REFRESH\"}" \
  | python3 -m json.tool
```

**Expected:** HTTP 200, `{"message": "Logged out"}`

**DB verification:**
```sql
SELECT revoked FROM refresh_tokens ORDER BY updated_at DESC LIMIT 1;
```
Expected: `revoked=true`

**Then try to use revoked refresh token:**
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$ADMIN_REFRESH\"}" \
  -o /dev/null -w "%{http_code}"
```
Expected: `401`

**PASS condition:** Logout returns 200, DB shows revoked=true, subsequent refresh returns 401.

---

#### CP-2.11 — GET /auth/me returns correct shape

*Login again to get a fresh token after logout:*
```bash
NEW_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "Test1234!", "registration_id": "", "fcm_token": ""}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $NEW_TOKEN" \
  | python3 -m json.tool
```

**Expected — all 8 fields present:**
```json
{
    "id": "uuid",
    "full_name": "Test Admin",
    "email": "admin@test.com",
    "role": "ADMIN",
    "registration_id": null,
    "class_id": null,
    "class_name": null,
    "status": "ACTIVE"
}
```

**PASS condition:** HTTP 200, all 8 fields present, admin's class_id and class_name explicitly null.

---

#### CP-2.12 — Protected route rejects missing/invalid token

```bash
# No token
curl -s http://localhost:8000/api/v1/auth/me -o /dev/null -w "%{http_code}"
```
Expected: `422` or `401`

```bash
# Invalid token
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer fake.token.here" \
  -o /dev/null -w "%{http_code}"
```
Expected: `401`

```bash
# Wrong format (no Bearer prefix)
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: $NEW_TOKEN" \
  -o /dev/null -w "%{http_code}"
```
Expected: `401`

**PASS condition:** All three return 4xx (not 200, not 500).

---

#### CP-2.13 — JWT payload has correct structure

```python
# Run as a quick script: python3 check_jwt.py
import jwt, os
from dotenv import load_dotenv
load_dotenv()

token = ""
payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"])

assert "sub" in payload,      f"MISSING: sub"
assert "role" in payload,     f"MISSING: role"
assert "class_id" in payload, f"MISSING: class_id (must be present even if null)"
assert "exp" in payload,      f"MISSING: exp"
assert payload["role"] == "ADMIN"
assert payload["class_id"] is None

print("JWT payload check PASSED")
print(f"  sub: {payload['sub']}")
print(f"  role: {payload['role']}")
print(f"  class_id: {payload['class_id']}")
```

**PASS condition:** Script prints "JWT payload check PASSED" with no AssertionError.

---

### Phase 2 Unit Tests

Create `Backend/tests/test_phase2.py`:

```python
# Backend/tests/test_phase2.py

import pytest
from unittest.mock import patch, MagicMock


class TestAdminSignup:

    def test_signup_returns_201(self, client):
        resp = client.post("/api/v1/auth/admin/signup", json={
            "full_name": "Admin User",
            "email": "newadmin@test.com",
            "password": "Test1234!"
        })
        assert resp.status_code == 201

    def test_signup_creates_pending_otp_user(self, client, db):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Admin User",
                "email": "admin_check@test.com",
                "password": "Test1234!"
            })
        from models.user import User
        user = db.query(User).filter_by(email="admin_check@test.com").first()
        assert user is not None
        assert user.role == "ADMIN"
        assert user.status == "PENDING_OTP"
        assert user.registration_id is None

    def test_signup_creates_otp_row(self, client, db):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "OTP Test",
                "email": "otp_test@test.com",
                "password": "Test1234!"
            })
        from models.user import OtpVerification
        otp = db.query(OtpVerification).filter_by(email="otp_test@test.com").first()
        assert otp is not None
        assert len(otp.otp_code) == 6
        assert otp.otp_code.isdigit()
        assert otp.used is False

    def test_duplicate_email_returns_409(self, client):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Admin One",
                "email": "dup@test.com",
                "password": "Test1234!"
            })
            resp = client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Admin Two",
                "email": "dup@test.com",
                "password": "Test1234!"
            })
        assert resp.status_code == 409

    def test_signup_response_shape(self, client):
        with patch("services.email_service.send_otp_email"):
            resp = client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Shape Test",
                "email": "shape@test.com",
                "password": "Test1234!"
            })
        assert resp.status_code == 201
        data = resp.json()
        assert "message" in data
        assert data["message"] == "OTP sent to your email"


class TestOtpVerify:

    def _create_admin_and_get_otp(self, client, db, email="verify@test.com"):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Verify Admin",
                "email": email,
                "password": "Test1234!"
            })
        from models.user import OtpVerification
        otp = db.query(OtpVerification).filter_by(email=email).first()
        return otp.otp_code

    def test_correct_otp_returns_200_with_tokens(self, client, db):
        otp = self._create_admin_and_get_otp(client, db, "otp_ok@test.com")
        resp = client.post("/api/v1/auth/admin/verify-otp", json={
            "email": "otp_ok@test.com", "otp": otp
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["role"] == "ADMIN"

    def test_correct_otp_activates_user(self, client, db):
        otp = self._create_admin_and_get_otp(client, db, "otp_activate@test.com")
        client.post("/api/v1/auth/admin/verify-otp", json={
            "email": "otp_activate@test.com", "otp": otp
        })
        from models.user import User
        user = db.query(User).filter_by(email="otp_activate@test.com").first()
        assert user.status == "ACTIVE"

    def test_correct_otp_creates_admin_profile(self, client, db):
        otp = self._create_admin_and_get_otp(client, db, "otp_profile@test.com")
        client.post("/api/v1/auth/admin/verify-otp", json={
            "email": "otp_profile@test.com", "otp": otp
        })
        from models.user import User, AdminProfile
        user = db.query(User).filter_by(email="otp_profile@test.com").first()
        profile = db.query(AdminProfile).filter_by(user_id=user.id).first()
        assert profile is not None

    def test_correct_otp_marks_as_used(self, client, db):
        otp = self._create_admin_and_get_otp(client, db, "otp_used@test.com")
        client.post("/api/v1/auth/admin/verify-otp", json={
            "email": "otp_used@test.com", "otp": otp
        })
        from models.user import OtpVerification
        otp_row = db.query(OtpVerification).filter_by(email="otp_used@test.com").first()
        assert otp_row.used is True

    def test_wrong_otp_returns_400(self, client, db):
        self._create_admin_and_get_otp(client, db, "otp_wrong@test.com")
        resp = client.post("/api/v1/auth/admin/verify-otp", json={
            "email": "otp_wrong@test.com", "otp": "000000"
        })
        assert resp.status_code == 400

    def test_expired_otp_returns_410(self, client, db):
        self._create_admin_and_get_otp(client, db, "otp_exp@test.com")
        from models.user import OtpVerification
        from sqlalchemy import text
        db.execute(text(
            "UPDATE otp_verifications SET expires_at = now() - interval '1 minute' "
            "WHERE email = 'otp_exp@test.com'"
        ))
        db.commit()
        resp = client.post("/api/v1/auth/admin/verify-otp", json={
            "email": "otp_exp@test.com", "otp": "123456"
        })
        assert resp.status_code == 410

    def test_verify_creates_refresh_token_in_db(self, client, db):
        otp = self._create_admin_and_get_otp(client, db, "otp_refresh@test.com")
        client.post("/api/v1/auth/admin/verify-otp", json={
            "email": "otp_refresh@test.com", "otp": otp
        })
        from models.user import User, RefreshToken
        user = db.query(User).filter_by(email="otp_refresh@test.com").first()
        token_row = db.query(RefreshToken).filter_by(user_id=user.id).first()
        assert token_row is not None
        assert token_row.revoked is False


class TestLogin:

    def _create_verified_admin(self, client, db, email="logintest@test.com"):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Login Admin", "email": email, "password": "Test1234!"
            })
        from models.user import OtpVerification
        otp = db.query(OtpVerification).filter_by(email=email).first().otp_code
        client.post("/api/v1/auth/admin/verify-otp", json={"email": email, "otp": otp})

    def test_admin_login_returns_200(self, client, db):
        self._create_verified_admin(client, db, "adminlogin@test.com")
        resp = client.post("/api/v1/auth/login", json={
            "email": "adminlogin@test.com",
            "password": "Test1234!",
            "registration_id": "",
            "fcm_token": ""
        })
        assert resp.status_code == 200

    def test_admin_login_response_has_all_user_fields(self, client, db):
        self._create_verified_admin(client, db, "adminfields@test.com")
        resp = client.post("/api/v1/auth/login", json={
            "email": "adminfields@test.com",
            "password": "Test1234!",
            "registration_id": "",
            "fcm_token": ""
        })
        user = resp.json()["user"]
        required_fields = ["id", "full_name", "email", "role", "class_id", "class_name", "registration_id"]
        for field in required_fields:
            assert field in user, f"MISSING field in login response: user.{field}"

    def test_admin_login_class_id_is_explicitly_null(self, client, db):
        self._create_verified_admin(client, db, "adminnull@test.com")
        resp = client.post("/api/v1/auth/login", json={
            "email": "adminnull@test.com", "password": "Test1234!",
            "registration_id": "", "fcm_token": ""
        })
        user = resp.json()["user"]
        assert user["class_id"] is None, "class_id must be null for admin — not missing, explicitly null"
        assert user["class_name"] is None
        assert user["registration_id"] is None

    def test_wrong_password_returns_401(self, client, db):
        self._create_verified_admin(client, db, "wrongpw@test.com")
        resp = client.post("/api/v1/auth/login", json={
            "email": "wrongpw@test.com", "password": "WrongPass!", "registration_id": "", "fcm_token": ""
        })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    def test_unknown_email_returns_401(self, client, db):
        resp = client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com", "password": "Test1234!", "registration_id": "", "fcm_token": ""
        })
        assert resp.status_code == 401

    def test_login_stores_tokens_in_db(self, client, db):
        self._create_verified_admin(client, db, "tokensdb@test.com")
        resp = client.post("/api/v1/auth/login", json={
            "email": "tokensdb@test.com", "password": "Test1234!",
            "registration_id": "", "fcm_token": ""
        })
        from models.user import User, RefreshToken
        user = db.query(User).filter_by(email="tokensdb@test.com").first()
        tokens = db.query(RefreshToken).filter_by(user_id=user.id, revoked=False).all()
        assert len(tokens) >= 1

    def test_fcm_token_stored_when_provided(self, client, db):
        self._create_verified_admin(client, db, "fcmtest@test.com")
        client.post("/api/v1/auth/login", json={
            "email": "fcmtest@test.com", "password": "Test1234!",
            "registration_id": "", "fcm_token": "test-fcm-device-token"
        })
        from models.user import User
        user = db.query(User).filter_by(email="fcmtest@test.com").first()
        assert user.fcm_token == "test-fcm-device-token"


class TestTokenRefresh:

    def _get_admin_tokens(self, client, db, email="refresh_admin@test.com"):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Refresh Admin", "email": email, "password": "Test1234!"
            })
        from models.user import OtpVerification
        otp = db.query(OtpVerification).filter_by(email=email).first().otp_code
        resp = client.post("/api/v1/auth/admin/verify-otp", json={"email": email, "otp": otp})
        return resp.json()["access_token"], resp.json()["refresh_token"]

    def test_refresh_returns_new_access_token(self, client, db):
        access, refresh = self._get_admin_tokens(client, db)
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_returns_different_token(self, client, db):
        access, refresh = self._get_admin_tokens(client, db, "refresh2@test.com")
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        new_access = resp.json()["access_token"]
        assert new_access != access

    def test_invalid_refresh_returns_401(self, client, db):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid-token-here"})
        assert resp.status_code == 401

    def test_revoked_refresh_returns_401(self, client, db):
        access, refresh = self._get_admin_tokens(client, db, "refresh3@test.com")
        client.post("/api/v1/auth/logout",
                    headers={"Authorization": f"Bearer {access}"},
                    json={"refresh_token": refresh})
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 401


class TestLogout:

    def test_logout_returns_200(self, client, db):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Logout Admin", "email": "logout@test.com", "password": "Test1234!"
            })
        from models.user import OtpVerification
        otp = db.query(OtpVerification).filter_by(email="logout@test.com").first().otp_code
        resp = client.post("/api/v1/auth/admin/verify-otp", json={"email": "logout@test.com", "otp": otp})
        access = resp.json()["access_token"]
        refresh = resp.json()["refresh_token"]
        logout_resp = client.post("/api/v1/auth/logout",
                                  headers={"Authorization": f"Bearer {access}"},
                                  json={"refresh_token": refresh})
        assert logout_resp.status_code == 200
        assert logout_resp.json()["message"] == "Logged out"

    def test_logout_revokes_token_in_db(self, client, db):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Revoke Admin", "email": "revoke@test.com", "password": "Test1234!"
            })
        from models.user import OtpVerification, User, RefreshToken
        otp = db.query(OtpVerification).filter_by(email="revoke@test.com").first().otp_code
        resp = client.post("/api/v1/auth/admin/verify-otp", json={"email": "revoke@test.com", "otp": otp})
        access = resp.json()["access_token"]
        refresh = resp.json()["refresh_token"]
        client.post("/api/v1/auth/logout",
                    headers={"Authorization": f"Bearer {access}"},
                    json={"refresh_token": refresh})
        user = db.query(User).filter_by(email="revoke@test.com").first()
        token_row = db.query(RefreshToken).filter_by(user_id=user.id).first()
        assert token_row.revoked is True


class TestGetMe:

    def test_me_returns_all_required_fields(self, client, admin_headers):
        resp = client.get("/api/v1/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        required = ["id", "full_name", "email", "role", "registration_id",
                    "class_id", "class_name", "status"]
        for field in required:
            assert field in data, f"MISSING: /auth/me response missing field '{field}'"

    def test_me_admin_class_fields_are_null(self, client, admin_headers):
        resp = client.get("/api/v1/auth/me", headers=admin_headers)
        data = resp.json()
        assert data["class_id"] is None
        assert data["class_name"] is None
        assert data["registration_id"] is None

    def test_me_without_token_returns_4xx(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code in [401, 422]

    def test_me_with_fake_token_returns_401(self, client):
        resp = client.get("/api/v1/auth/me",
                          headers={"Authorization": "Bearer fake.token.here"})
        assert resp.status_code == 401

    def test_me_returns_correct_role(self, client, admin_headers):
        resp = client.get("/api/v1/auth/me", headers=admin_headers)
        assert resp.json()["role"] == "ADMIN"

    def test_me_returns_active_status(self, client, admin_headers):
        resp = client.get("/api/v1/auth/me", headers=admin_headers)
        assert resp.json()["status"] == "ACTIVE"
```

**Run Phase 2 tests:**
```bash
cd Backend
pytest tests/test_phase2.py -v
```

**Phase 2 Gate:** All tests PASS + all 13 manual CPs PASS → proceed to Phase 3.

---

## PHASE 3 — Classes & Provisioning Verification

### Manual Checkpoints

All commands below assume you have `ADMIN_TOKEN` set from a fresh admin login.

```bash
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "Test1234!", "registration_id": "", "fcm_token": ""}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

---

#### CP-3.1 — Create class returns correct shape and creates analytics row

```bash
CLASS_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/classes \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"class_name": "Batch A 2026", "description": "Test class", "academic_year": "2026"}')

echo $CLASS_RESPONSE | python3 -m json.tool

CLASS_ID=$(echo $CLASS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Class ID: $CLASS_ID"
```

**Expected response:**
```json
{
    "id": "uuid",
    "class_name": "Batch A 2026",
    "description": "Test class",
    "academic_year": "2026",
    "status": "ACTIVE",
    "created_at": "timestamp"
}
```

**DB verification:**
```sql
SELECT COUNT(*) FROM class_analytics WHERE class_id='';
```
Expected: `1`

```sql
SELECT avg_completion, total_students FROM class_analytics WHERE class_id='';
```
Expected: `0`, `0` (all zeros initialized)

**PASS condition:** HTTP 201, class_analytics row exists with zeros.

---

#### CP-3.2 — GET /classes returns class list with counts

```bash
curl -s http://localhost:8000/api/v1/classes \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | python3 -m json.tool
```

**Expected:**
```json
{
    "classes": [
        {
            "id": "uuid",
            "class_name": "Batch A 2026",
            "student_count": 0,
            "mentor_count": 0,
            "status": "ACTIVE"
        }
    ]
}
```

**PASS condition:** HTTP 200, class created in CP-3.1 visible, counts are 0.

---

#### CP-3.3 — Provision a mentor manually

```bash
MENTOR_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/provision/manual/mentor \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"class_id\": \"$CLASS_ID\", \"full_name\": \"Mentor One\", \"email\": \"mentor@test.com\", \"password\": \"Mentor1234!\", \"is_primary_mentor\": true}")

echo $MENTOR_RESPONSE | python3 -m json.tool
MENTOR_REG_ID=$(echo $MENTOR_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['registration_id'])")
MENTOR_ID=$(echo $MENTOR_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Mentor Reg ID: $MENTOR_REG_ID"
```

**Expected response:**
```json
{
    "id": "uuid",
    "registration_id": "MENTOR-XXXXXXXX",
    "message": "Invitation sent"
}
```

**DB verification:**
```sql
SELECT role, status, registration_id FROM users WHERE email='mentor@test.com';
```
Expected: `role=MENTOR`, `status=ACTIVE`, `registration_id` starts with `MENTOR-`

```sql
SELECT is_primary_mentor, status, member_role 
FROM class_memberships WHERE user_id='';
```
Expected: `is_primary_mentor=true`, `status=ACTIVE`, `member_role=MENTOR`

**Check Brevo email:** Mentor invitation email received with credentials.

**PASS condition:** HTTP 201, DB checks pass, email received.

---

#### CP-3.4 — Mentor login works with class data

```bash
MENTOR_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"mentor@test.com\", \"password\": \"Mentor1234!\", \"registration_id\": \"$MENTOR_REG_ID\", \"fcm_token\": \"\"}" \
  | python3 -m json.tool)

echo $MENTOR_TOKEN
```

**Expected — key checks:**
- HTTP 200
- `user.role = "MENTOR"`
- `user.class_id = "<CLASS_ID>"` — not null
- `user.class_name = "Batch A 2026"` — not null

```bash
MENTOR_ACCESS=$(echo $MENTOR_TOKEN | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['access_token'])")
```

**PASS condition:** HTTP 200, class_id and class_name populated correctly.

---

#### CP-3.5 — GET /classes/my-classes returns mentor's class

```bash
curl -s http://localhost:8000/api/v1/classes/my-classes \
  -H "Authorization: Bearer $MENTOR_ACCESS" \
  | python3 -m json.tool
```

**Expected:**
```json
{
    "classes": [
        {
            "id": "uuid",
            "class_name": "Batch A 2026",
            "status": "ACTIVE",
            "is_primary_mentor": true
        }
    ]
}
```

**PASS condition:** HTTP 200, 1 class returned, `is_primary_mentor=true`.

---

#### CP-3.6 — Provision student manually (PENDING status)

```bash
STUDENT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/provision/manual/student \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"class_id\": \"$CLASS_ID\", \"full_name\": \"Student One\", \"email\": \"student@test.com\", \"password\": \"Student1234!\", \"registration_id\": \"ROLL001\"}")

echo $STUDENT_RESPONSE | python3 -m json.tool
STUDENT_ID=$(echo $STUDENT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
```

**Expected:** HTTP 201, message contains "Awaiting approval"

**DB verification — CRITICAL:**
```sql
SELECT status FROM class_memberships 
WHERE user_id='' AND class_id='';
```
Expected: **`PENDING`** — this MUST NOT be `ACTIVE`

**PASS condition:** HTTP 201, class_memberships.status is exactly `PENDING`.

---

#### CP-3.7 — Student login blocked while PENDING

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "student@test.com", "password": "Student1234!", "registration_id": "ROLL001", "fcm_token": ""}' \
  | python3 -m json.tool
```

**Expected:**
```json
{
    "detail": "Account pending approval. Please wait for your mentor to approve your access."
}
```
HTTP status: `403`

**PASS condition:** HTTP 403, message contains "pending approval".

---

#### CP-3.8 — Approvals list shows pending student

```bash
curl -s "http://localhost:8000/api/v1/classes/$CLASS_ID/approvals" \
  -H "Authorization: Bearer $MENTOR_ACCESS" \
  | python3 -m json.tool
```

**Expected:**
```json
{
    "pending_count": 1,
    "pending": [
        {
            "student_id": "uuid",
            "full_name": "Student One",
            "email": "student@test.com",
            "registration_id": "ROLL001",
            "requested_at": "timestamp",
            "joined_via": "MANUAL"
        }
    ]
}
```

**PASS condition:** HTTP 200, `pending_count=1`, all 6 fields present in pending array.

---

#### CP-3.9 — Approve student creates analytics row and notification

```bash
curl -s -X PATCH "http://localhost:8000/api/v1/classes/$CLASS_ID/students/$STUDENT_ID/approve" \
  -H "Authorization: Bearer $MENTOR_ACCESS" \
  -H "Content-Type: application/json" \
  -d '{}' \
  | python3 -m json.tool
```

**Expected:**
```json
{ "message": "Student approved", "student_id": "uuid" }
```

**DB verification (all 4 must pass):**

```sql
-- 1. Membership is now ACTIVE
SELECT status FROM class_memberships 
WHERE user_id='' AND class_id='';
```
Expected: `ACTIVE`

```sql
-- 2. Student analytics row created with zeros
SELECT total_assigned, total_submitted, completion_rate, risk_level 
FROM student_analytics 
WHERE student_id='' AND class_id='';
```
Expected: `0, 0, 0.00, NORMAL`

```sql
-- 3. Approval notification created
SELECT notification_type, title FROM notifications 
WHERE user_id='' AND notification_type='STUDENT_APPROVED';
```
Expected: 1 row

```sql
-- 4. Approvals list is now empty
-- Run CP-3.8 again after this
```

**PASS condition:** HTTP 200, all 4 DB checks correct.

---

#### CP-3.10 — Student login succeeds after approval

```bash
STUDENT_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "student@test.com", "password": "Student1234!", "registration_id": "ROLL001", "fcm_token": ""}' \
  | python3 -m json.tool)

echo $STUDENT_TOKEN
```

**Expected:**
- HTTP 200
- `user.role = "STUDENT"`
- `user.class_id = "<CLASS_ID>"`
- `user.class_name = "Batch A 2026"`

**PASS condition:** HTTP 200, class_id and class_name populated.

---

#### CP-3.11 — Reject a second student

Provision second student:
```bash
curl -s -X POST http://localhost:8000/api/v1/provision/manual/student \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"class_id\": \"$CLASS_ID\", \"full_name\": \"Student Two\", \"email\": \"student2@test.com\", \"password\": \"Student1234!\", \"registration_id\": \"ROLL002\"}"
```

Get student2 ID:
```bash
STUDENT2_ID=$(psql $DATABASE_URL -t -c "SELECT id FROM users WHERE email='student2@test.com';" | tr -d ' ')
```

Reject:
```bash
curl -s -X PATCH "http://localhost:8000/api/v1/classes/$CLASS_ID/students/$STUDENT2_ID/reject" \
  -H "Authorization: Bearer $MENTOR_ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Duplicate enrollment"}' \
  | python3 -m json.tool
```

**DB verification:**
```sql
SELECT status, rejection_reason FROM class_memberships 
WHERE user_id='';
```
Expected: `status=REJECTED`, `rejection_reason=Duplicate enrollment`

```sql
SELECT COUNT(*) FROM notifications 
WHERE user_id='' AND notification_type='STUDENT_REJECTED';
```
Expected: `1`

**PASS condition:** HTTP 200, status=REJECTED in DB, notification created.

---

#### CP-3.12 — Archive class sends notifications

```bash
curl -s -X PATCH "http://localhost:8000/api/v1/classes/$CLASS_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "ARCHIVED"}' \
  | python3 -m json.tool
```

**Expected:** returned object has `"status": "ARCHIVED"`

**DB verification:**
```sql
SELECT COUNT(*) FROM notifications WHERE notification_type='CLASS_ARCHIVED';
```
Expected: at least 1 (one per active member — should be at least 2: approved student + mentor)

**PASS condition:** HTTP 200, status=ARCHIVED, CLASS_ARCHIVED notifications exist.

---

#### CP-3.13 — Bulk import template downloads correctly

```bash
curl -s http://localhost:8000/api/v1/provision/bulk-import/template \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o template.xlsx

# Verify it's a valid xlsx (not an HTML error page)
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('template.xlsx')
print('Sheet names:', wb.sheetnames)
assert 'Classes' in wb.sheetnames
assert 'Mentors' in wb.sheetnames
assert 'Students' in wb.sheetnames
print('Template is valid XLSX with 3 correct sheets')
"
```

**Verify column headers in each sheet:**
```python
import openpyxl
wb = openpyxl.load_workbook('template.xlsx')

classes_headers = [cell.value for cell in wb['Classes'][1]]
assert 'class_name' in classes_headers
assert 'description' in classes_headers

mentors_headers = [cell.value for cell in wb['Mentors'][1]]
assert 'class_name' in mentors_headers
assert 'mentor_name' in mentors_headers
assert 'mentor_email' in mentors_headers
assert 'is_primary_mentor' in mentors_headers

students_headers = [cell.value for cell in wb['Students'][1]]
assert 'class_name' in students_headers
assert 'student_name' in students_headers
assert 'student_email' in students_headers
assert 'registration_id' in students_headers

print("All column headers correct")
```

**PASS condition:** File downloads, opens, has 3 sheets with correct column names.

---

#### CP-3.14 — Bulk import processes Excel file

Fill `template.xlsx` with:
- Sheet1 Classes: `Bulk Class 1`
- Sheet2 Mentors: mentor email `bulk_mentor@test.com`
- Sheet3 Students: student email `bulk_student@test.com`, registration_id `BULK001`

```bash
BATCH_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/provision/bulk-import \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@template.xlsx")

echo $BATCH_RESPONSE | python3 -m json.tool
BATCH_ID=$(echo $BATCH_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['batch_id'])")
```

**Poll until complete:**
```bash
for i in {1..15}; do
  STATUS=$(curl -s "http://localhost:8000/api/v1/provision/bulk-import/$BATCH_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
  echo "Attempt $i: $STATUS"
  if [ "$STATUS" = "COMPLETED" ] || [ "$STATUS" = "PARTIAL" ]; then
    break
  fi
  sleep 2
done
```

**DB verification:**
```sql
SELECT COUNT(*) FROM users WHERE email='bulk_mentor@test.com';
SELECT COUNT(*) FROM users WHERE email='bulk_student@test.com';
SELECT status FROM class_memberships WHERE user_id=(SELECT id FROM users WHERE email='bulk_student@test.com');
```
Expected: 1, 1, `PENDING`

**PASS condition:** HTTP 202, polling reaches COMPLETED/PARTIAL, DB records created, student status is PENDING.

---

#### CP-3.15 — GET /classes/{class_id}/students returns all required fields

*Create a fresh class and approve a student for this check if needed.*

```bash
curl -s "http://localhost:8000/api/v1/classes/$CLASS_ID/students" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | python3 -m json.tool
```

**Verify each student object has ALL of these fields:**
- `id`
- `full_name`
- `email`
- `registration_id`
- `membership_status` ← must be this name, NOT `status`
- `risk_level`
- `completion_rate`
- `joined_via`
- `joined_at`

**PASS condition:** HTTP 200, all 9 fields present per student, field name is `membership_status` not `status`.

---

#### CP-3.16 — Role enforcement — mentor cannot create class

```bash
curl -s -X POST http://localhost:8000/api/v1/classes \
  -H "Authorization: Bearer $MENTOR_ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"class_name": "Unauthorized Class"}' \
  -o /dev/null -w "%{http_code}"
```

**Expected:** `403`

Also test student cannot access approvals:
```bash
STUDENT_ACCESS=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "student@test.com", "password": "Student1234!", "registration_id": "ROLL001", "fcm_token": ""}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

curl -s "http://localhost:8000/api/v1/classes/$CLASS_ID/approvals" \
  -H "Authorization: Bearer $STUDENT_ACCESS" \
  -o /dev/null -w "%{http_code}"
```
Expected: `403`

**PASS condition:** Both return 403.

---

### Phase 3 Unit Tests

Create `Backend/tests/test_phase3.py`:

```python
# Backend/tests/test_phase3.py

import pytest
from unittest.mock import patch, MagicMock


class TestClassCreation:

    def test_create_class_returns_201(self, client, admin_headers):
        resp = client.post("/api/v1/classes",
                           headers=admin_headers,
                           json={"class_name": "Test Class", "description": "Desc", "academic_year": "2026"})
        assert resp.status_code == 201

    def test_create_class_response_shape(self, client, admin_headers):
        resp = client.post("/api/v1/classes",
                           headers=admin_headers,
                           json={"class_name": "Shape Class"})
        data = resp.json()
        required = ["id", "class_name", "status", "created_at"]
        for field in required:
            assert field in data, f"MISSING: {field} in create class response"
        assert data["status"] == "ACTIVE"

    def test_create_class_creates_analytics_row(self, client, db, admin_headers):
        resp = client.post("/api/v1/classes",
                           headers=admin_headers,
                           json={"class_name": "Analytics Class"})
        class_id = resp.json()["id"]
        from models.analytics import ClassAnalytics
        import uuid
        row = db.query(ClassAnalytics).filter_by(class_id=uuid.UUID(class_id)).first()
        assert row is not None, "class_analytics row must be created on class creation"
        assert row.total_students == 0
        assert float(row.avg_completion) == 0.0

    def test_mentor_cannot_create_class(self, client, admin_headers):
        # Create mentor first
        with patch("services.email_service.send_invitation_email"):
            class_resp = client.post("/api/v1/classes",
                                     headers=admin_headers,
                                     json={"class_name": "Mentor Test Class"})
            class_id = class_resp.json()["id"]
            mentor_resp = client.post("/api/v1/provision/manual/mentor",
                                      headers=admin_headers,
                                      json={
                                          "class_id": class_id,
                                          "full_name": "Auth Mentor",
                                          "email": "auth_mentor@test.com",
                                          "password": "Mentor1234!",
                                          "is_primary_mentor": True
                                      })
        reg_id = mentor_resp.json()["registration_id"]
        login = client.post("/api/v1/auth/login", json={
            "email": "auth_mentor@test.com", "password": "Mentor1234!",
            "registration_id": reg_id, "fcm_token": ""
        })
        mentor_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        resp = client.post("/api/v1/classes",
                           headers=mentor_headers,
                           json={"class_name": "Hack Class"})
        assert resp.status_code == 403

    def test_get_classes_returns_list(self, client, admin_headers):
        client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "List Class 1"})
        client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "List Class 2"})
        resp = client.get("/api/v1/classes", headers=admin_headers)
        assert resp.status_code == 200
        assert "classes" in resp.json()
        assert len(resp.json()["classes"]) >= 2

    def test_get_classes_includes_counts(self, client, admin_headers):
        client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "Count Class"})
        resp = client.get("/api/v1/classes", headers=admin_headers)
        classes = resp.json()["classes"]
        for c in classes:
            assert "student_count" in c
            assert "mentor_count" in c


class TestProvisioning:

    def _create_class(self, client, admin_headers):
        resp = client.post("/api/v1/classes",
                           headers=admin_headers,
                           json={"class_name": "Provision Class"})
        return resp.json()["id"]

    def test_provision_mentor_returns_mentor_reg_id(self, client, admin_headers):
        class_id = self._create_class(client, admin_headers)
        with patch("services.email_service.send_invitation_email"):
            resp = client.post("/api/v1/provision/manual/mentor",
                               headers=admin_headers,
                               json={
                                   "class_id": class_id,
                                   "full_name": "Test Mentor",
                                   "email": "prov_mentor@test.com",
                                   "password": "Mentor1234!",
                                   "is_primary_mentor": True
                               })
        assert resp.status_code == 201
        data = resp.json()
        assert "registration_id" in data
        assert data["registration_id"].startswith("MENTOR-")

    def test_provision_mentor_creates_active_membership(self, client, db, admin_headers):
        class_id = self._create_class(client, admin_headers)
        with patch("services.email_service.send_invitation_email"):
            resp = client.post("/api/v1/provision/manual/mentor",
                               headers=admin_headers,
                               json={
                                   "class_id": class_id,
                                   "full_name": "Active Mentor",
                                   "email": "active_mentor@test.com",
                                   "password": "Mentor1234!",
                                   "is_primary_mentor": False
                               })
        import uuid
        mentor_id = uuid.UUID(resp.json()["id"])
        from models.class_ import ClassMembership
        membership = db.query(ClassMembership).filter_by(user_id=mentor_id).first()
        assert membership.status == "ACTIVE", "Mentor membership must start as ACTIVE"

    def test_provision_student_creates_pending_membership(self, client, db, admin_headers):
        class_id = self._create_class(client, admin_headers)
        with patch("services.email_service.send_invitation_email"):
            resp = client.post("/api/v1/provision/manual/student",
                               headers=admin_headers,
                               json={
                                   "class_id": class_id,
                                   "full_name": "Pending Student",
                                   "email": "pending_stud@test.com",
                                   "password": "Student1234!",
                                   "registration_id": "PEND001"
                               })
        assert resp.status_code == 201
        import uuid
        student_id = uuid.UUID(resp.json()["id"])
        from models.class_ import ClassMembership
        membership = db.query(ClassMembership).filter_by(user_id=student_id).first()
        assert membership.status == "PENDING", (
            "CRITICAL: Student membership must be PENDING on creation. "
            f"Found: {membership.status}"
        )

    def test_duplicate_email_returns_409_for_mentor(self, client, admin_headers):
        class_id = self._create_class(client, admin_headers)
        with patch("services.email_service.send_invitation_email"):
            client.post("/api/v1/provision/manual/mentor",
                        headers=admin_headers,
                        json={"class_id": class_id, "full_name": "M1", "email": "dup_m@test.com",
                              "password": "P", "is_primary_mentor": False})
            resp = client.post("/api/v1/provision/manual/mentor",
                               headers=admin_headers,
                               json={"class_id": class_id, "full_name": "M2", "email": "dup_m@test.com",
                                     "password": "P", "is_primary_mentor": False})
        assert resp.status_code == 409

    def test_duplicate_registration_id_returns_409_for_student(self, client, admin_headers):
        class_id = self._create_class(client, admin_headers)
        with patch("services.email_service.send_invitation_email"):
            client.post("/api/v1/provision/manual/student",
                        headers=admin_headers,
                        json={"class_id": class_id, "full_name": "S1", "email": "s1@test.com",
                              "password": "P", "registration_id": "DUPROLL"})
            resp = client.post("/api/v1/provision/manual/student",
                               headers=admin_headers,
                               json={"class_id": class_id, "full_name": "S2", "email": "s2@test.com",
                                     "password": "P", "registration_id": "DUPROLL"})
        assert resp.status_code == 409


class TestApprovalFlow:

    def _setup_class_with_pending_student(self, client, db, admin_headers):
        """Helper: create class + mentor + pending student, return their IDs + mentor token."""
        class_resp = client.post("/api/v1/classes", headers=admin_headers,
                                 json={"class_name": "Approval Class"})
        class_id = class_resp.json()["id"]

        with patch("services.email_service.send_invitation_email"):
            mentor_resp = client.post("/api/v1/provision/manual/mentor",
                                      headers=admin_headers,
                                      json={"class_id": class_id, "full_name": "App Mentor",
                                            "email": "app_mentor@test.com",
                                            "password": "Mentor1234!", "is_primary_mentor": True})
            reg_id = mentor_resp.json()["registration_id"]
            mentor_id = mentor_resp.json()["id"]

            student_resp = client.post("/api/v1/provision/manual/student",
                                       headers=admin_headers,
                                       json={"class_id": class_id, "full_name": "App Student",
                                             "email": "app_student@test.com",
                                             "password": "Student1234!", "registration_id": "APP001"})
            student_id = student_resp.json()["id"]

        login = client.post("/api/v1/auth/login", json={
            "email": "app_mentor@test.com", "password": "Mentor1234!",
            "registration_id": reg_id, "fcm_token": ""
        })
        mentor_token = login.json()["access_token"]
        mentor_headers = {"Authorization": f"Bearer {mentor_token}"}

        return class_id, student_id, mentor_headers

    def test_pending_student_blocked_from_login(self, client, db, admin_headers):
        self._setup_class_with_pending_student(client, db, admin_headers)
        resp = client.post("/api/v1/auth/login", json={
            "email": "app_student@test.com", "password": "Student1234!",
            "registration_id": "APP001", "fcm_token": ""
        })
        assert resp.status_code == 403
        assert "pending" in resp.json()["detail"].lower()

    def test_approvals_list_returns_pending_student(self, client, db, admin_headers):
        class_id, student_id, mentor_headers = self._setup_class_with_pending_student(client, db, admin_headers)
        resp = client.get(f"/api/v1/classes/{class_id}/approvals", headers=mentor_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["pending_count"] == 1
        assert len(data["pending"]) == 1
        pending = data["pending"][0]
        for field in ["student_id", "full_name", "email", "registration_id", "requested_at", "joined_via"]:
            assert field in pending, f"MISSING field in approvals: {field}"

    def test_approve_changes_status_to_active(self, client, db, admin_headers):
        class_id, student_id, mentor_headers = self._setup_class_with_pending_student(client, db, admin_headers)
        with patch("services.fcm_service.send_single_fcm"):
            resp = client.patch(f"/api/v1/classes/{class_id}/students/{student_id}/approve",
                                headers=mentor_headers, json={})
        assert resp.status_code == 200
        import uuid
        from models.class_ import ClassMembership
        membership = db.query(ClassMembership).filter_by(
            user_id=uuid.UUID(student_id),
            class_id=uuid.UUID(class_id)
        ).first()
        assert membership.status == "ACTIVE"

    def test_approve_creates_student_analytics_row(self, client, db, admin_headers):
        class_id, student_id, mentor_headers = self._setup_class_with_pending_student(client, db, admin_headers)
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{class_id}/students/{student_id}/approve",
                         headers=mentor_headers, json={})
        from models.analytics import StudentAnalytics
        import uuid
        row = db.query(StudentAnalytics).filter_by(
            student_id=uuid.UUID(student_id),
            class_id=uuid.UUID(class_id)
        ).first()
        assert row is not None, "student_analytics row must be created on approval"
        assert row.total_assigned == 0
        assert row.risk_level == "NORMAL"

    def test_approve_creates_notification(self, client, db, admin_headers):
        class_id, student_id, mentor_headers = self._setup_class_with_pending_student(client, db, admin_headers)
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{class_id}/students/{student_id}/approve",
                         headers=mentor_headers, json={})
        from models.notification import Notification
        import uuid
        notif = db.query(Notification).filter_by(
            user_id=uuid.UUID(student_id),
            notification_type='STUDENT_APPROVED'
        ).first()
        assert notif is not None

    def test_student_can_login_after_approval(self, client, db, admin_headers):
        class_id, student_id, mentor_headers = self._setup_class_with_pending_student(client, db, admin_headers)
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{class_id}/students/{student_id}/approve",
                         headers=mentor_headers, json={})
        resp = client.post("/api/v1/auth/login", json={
            "email": "app_student@test.com", "password": "Student1234!",
            "registration_id": "APP001", "fcm_token": ""
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "STUDENT"
        assert resp.json()["user"]["class_id"] == class_id

    def test_reject_changes_status_to_rejected(self, client, db, admin_headers):
        class_id, student_id, mentor_headers = self._setup_class_with_pending_student(client, db, admin_headers)
        with patch("services.fcm_service.send_single_fcm"):
            resp = client.patch(f"/api/v1/classes/{class_id}/students/{student_id}/reject",
                                headers=mentor_headers,
                                json={"reason": "Test rejection"})
        assert resp.status_code == 200
        from models.class_ import ClassMembership
        import uuid
        membership = db.query(ClassMembership).filter_by(user_id=uuid.UUID(student_id)).first()
        assert membership.status == "REJECTED"
        assert membership.rejection_reason == "Test rejection"

    def test_students_list_field_name_is_membership_status_not_status(self, client, db, admin_headers):
        """CRITICAL: field must be 'membership_status' not 'status' to avoid mismatch with users.status."""
        class_id, student_id, mentor_headers = self._setup_class_with_pending_student(client, db, admin_headers)
        resp = client.get(f"/api/v1/classes/{class_id}/students", headers=mentor_headers)
        assert resp.status_code == 200
        students = resp.json()["students"]
        if students:
            assert "membership_status" in students[0], (
                "FIELD MISMATCH: student list must use 'membership_status' not 'status'. "
                "Flutter model expects 'membership_status'."
            )
            assert "status" not in students[0], (
                "FIELD MISMATCH: 'status' must not appear in student list. "
                "Use 'membership_status' instead."
            )


class TestBulkImport:

    def test_template_downloads_as_xlsx(self, client, admin_headers):
        resp = client.get("/api/v1/provision/bulk-import/template", headers=admin_headers)
        assert resp.status_code == 200
        assert 'spreadsheet' in resp.headers.get('content-type', '').lower() or \
               'xlsx' in resp.headers.get('content-type', '').lower() or \
               'openxmlformats' in resp.headers.get('content-type', '').lower()

    def test_template_has_three_correct_sheets(self, client, admin_headers):
        import io
        import openpyxl
        resp = client.get("/api/v1/provision/bulk-import/template", headers=admin_headers)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        assert 'Classes' in wb.sheetnames, f"Missing 'Classes' sheet. Got: {wb.sheetnames}"
        assert 'Mentors' in wb.sheetnames, f"Missing 'Mentors' sheet."
        assert 'Students' in wb.sheetnames, f"Missing 'Students' sheet."

    def test_bulk_import_returns_202_with_batch_id(self, client, admin_headers):
        import io
        import openpyxl
        # Create minimal valid xlsx
        wb = openpyxl.Workbook()
        ws_classes = wb.active
        ws_classes.title = 'Classes'
        ws_classes.append(['class_name', 'description', 'academic_year'])
        ws_classes.append(['Bulk Test Class', 'Desc', '2026'])
        ws_mentors = wb.create_sheet('Mentors')
        ws_mentors.append(['class_name', 'mentor_name', 'mentor_email', 'mentor_password', 'is_primary_mentor'])
        ws_students = wb.create_sheet('Students')
        ws_students.append(['class_name', 'student_name', 'student_email', 'student_password', 'registration_id', 'roll_no'])
        
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        
        with patch("services.email_service.send_invitation_email"):
            resp = client.post("/api/v1/provision/bulk-import",
                               headers=admin_headers,
                               files={"file": ("import.xlsx", buf.read(),
                                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert resp.status_code == 202
        assert "batch_id" in resp.json()
        assert resp.json()["status"] == "UPLOADED"

    def test_bulk_import_batch_status_endpoint(self, client, admin_headers):
        import io
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Classes'
        ws.append(['class_name', 'description', 'academic_year'])
        wb.create_sheet('Mentors').append(['class_name', 'mentor_name', 'mentor_email', 'mentor_password', 'is_primary_mentor'])
        wb.create_sheet('Students').append(['class_name', 'student_name', 'student_email', 'student_password', 'registration_id', 'roll_no'])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        
        with patch("services.email_service.send_invitation_email"):
            batch_resp = client.post("/api/v1/provision/bulk-import",
                                     headers=admin_headers,
                                     files={"file": ("import.xlsx", buf.read(),
                                                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        batch_id = batch_resp.json()["batch_id"]
        
        # Poll status
        import time
        for _ in range(10):
            status_resp = client.get(f"/api/v1/provision/bulk-import/{batch_id}", headers=admin_headers)
            assert status_resp.status_code == 200
            status = status_resp.json()["status"]
            if status in ("COMPLETED", "PARTIAL", "FAILED"):
                break
            time.sleep(0.5)
        
        final = client.get(f"/api/v1/provision/bulk-import/{batch_id}", headers=admin_headers).json()
        assert "total_rows" in final
        assert "success_rows" in final
        assert "failed_rows" in final
        assert "errors" in final
```

**Run Phase 3 tests:**
```bash
cd Backend
pytest tests/test_phase3.py -v
```

---

## Full Test Suite Runner

Run all phases together:

```bash
cd Backend

# Run all phases in order
pytest tests/test_phase1.py tests/test_phase2.py tests/test_phase3.py -v --tb=short

# Or run with summary only
pytest tests/ -v --tb=short -q

# Run single phase
pytest tests/test_phase1.py -v

# Run specific test class
pytest tests/test_phase3.py::TestApprovalFlow -v

# Run specific test
pytest tests/test_phase3.py::TestApprovalFlow::test_approve_creates_student_analytics_row -v

# Stop on first failure
pytest tests/ -x -v

# Show print statements during test
pytest tests/ -v -s
```

---

## Phase Gate Summary

|
 Phase 
|
 Manual CPs 
|
 Unit Tests 
|
 Gate 
|
|
---
|
---
|
---
|
---
|
|
 Phase 1 
|
 11 checkpoints 
|
 22 tests 
|
 All pass → proceed to Phase 2 
|
|
 Phase 2 
|
 13 checkpoints 
|
 ~30 tests 
|
 All pass → proceed to Phase 3 
|
|
 Phase 3 
|
 16 checkpoints 
|
 ~25 tests 
|
 All pass → proceed to Phase 4 
|

**Total: 40 manual checkpoints + 77 unit tests covering Phases 1–3.**

---

## Common Failures and Their Fixes

|
 Failure 
|
 Root Cause 
|
 Fix 
|
|
---
|
---
|
---
|
|
`test_class_memberships_status_check_includes_pending`
 fails 
|
 PENDING missing from CHECK constraint 
|
 Add 
`PENDING`
,
`REJECTED`
 to class_memberships.status CHECK in migration 
|
|
`test_users_status_default_is_active_not_pending`
 fails 
|
 users.status DEFAULT is bare 
`'PENDING'`
|
 Change DEFAULT to 
`'ACTIVE'`
 — account status and membership status are separate 
|
|
 CP-3.6 shows ACTIVE not PENDING 
|
 student provisioning sets ACTIVE 
|
 Change 
`status='ACTIVE'`
 to 
`status='PENDING'`
 in student INSERT 
|
|
 CP-2.6 missing 
`class_id`
 field 
|
`/auth/login`
 not joining class_memberships 
|
 Add LEFT JOIN in login handler 
|
|
`test_students_list_field_name_is_membership_status_not_status`
 fails 
|
 Returning 
`status`
 instead of 
`membership_status`
|
 Map 
`cm.status`
 to 
`membership_status`
 in query response 
|
|
`test_student_analytics_uses_numeric_not_interval`
 fails 
|
`INTERVAL`
 type used for delay 
|
 Change column type to 
`NUMERIC(6,2)`
|
|
 Bulk import student status is ACTIVE 
|
 Import sets ACTIVE 
|
 Change to 
`status='PENDING'`
 in bulk import Sheet 3 handler 
|
|
 APScheduler jobs lost on restart 
|
 In-memory jobstore 
|
 Add SQLAlchemyJobStore with DATABASE_URL 
|

---

*Verification suite version: 1.0 | Covers Phase 1 Foundation + Phase 2 Auth + Phase 3 Classes & Provisioning*
Done






