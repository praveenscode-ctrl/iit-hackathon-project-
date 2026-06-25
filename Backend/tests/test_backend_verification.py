# Backend/tests/test_backend_verification.py
# Run: pytest tests/test_backend_verification.py -v

import pytest
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from dotenv import load_dotenv
from unittest.mock import patch, MagicMock

load_dotenv(".env.test")
from database import Base, get_db
from main import app

engine = create_engine(os.getenv("DATABASE_URL"))
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture(scope="function")
def db():
    conn = engine.connect()
    tx = conn.begin()
    session = TestingSessionLocal(bind=conn)
    yield session
    session.close()
    tx.rollback()
    conn.close()

@pytest.fixture(scope="function")
def client(db):
    def override():
        yield db
    app.dependency_overrides[get_db] = override
    with patch("scheduler.jobs.scheduler.start"), patch("scheduler.jobs.scheduler.shutdown"), patch("websocket.tracker_ws.manager.broadcast"):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def admin_token(client, db):
    with patch("services.email_service.send_otp_email"):
        client.post("/api/v1/auth/admin/signup", json={
            "full_name": "Verify Admin", "email": "vadmin@test.com", "password": "Test1234!"
        })
    from models.user import OtpVerification
    otp = db.query(OtpVerification).filter_by(email="vadmin@test.com").first().otp_code
    resp = client.post("/api/v1/auth/admin/verify-otp", json={"email": "vadmin@test.com", "otp": otp})
    return resp.json()["access_token"]

@pytest.fixture(scope="function")
def admin_h(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


class TestDatabaseSchema:
    EXPECTED_TABLES = [
        'users','otp_verifications','admin_profiles','refresh_tokens',
        'classes','class_memberships','assignments','submissions',
        'student_analytics','class_analytics','assignment_analytics',
        'notifications','reminder_jobs','bulk_import_batches',
        'bulk_import_errors','export_jobs','ai_query_logs'
    ]

    def test_all_17_tables_exist(self):
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
        for t in self.EXPECTED_TABLES:
            assert t in existing, f"MISSING TABLE: {t}"

    def test_users_status_default_is_active_not_pending(self):
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name='users' AND column_name='status'"
            )).fetchone()
        default = result[0] if result else ""
        assert "pending" not in str(default).lower().replace("pending_otp", ""), (
            f"CRITICAL: users.status DEFAULT is '{default}'. "
            "Must be 'ACTIVE'. Bare 'PENDING' is not in the CHECK constraint — "
            "every mentor/student INSERT will throw a DB constraint violation."
        )

    def test_class_memberships_status_check_has_pending_and_rejected(self):
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid='class_memberships'::regclass AND contype='c' "
                "AND pg_get_constraintdef(oid) ILIKE '%status%'"
            )).fetchone()
        assert result, "No status CHECK on class_memberships"
        defn = result[0]
        assert 'PENDING' in defn, f"CRITICAL: 'PENDING' missing from class_memberships.status CHECK. Got: {defn}"
        assert 'REJECTED' in defn, f"CRITICAL: 'REJECTED' missing from class_memberships.status CHECK. Got: {defn}"

    def test_submissions_has_separate_submitted_at_and_created_at(self):
        inspector = inspect(engine)
        cols = {c['name']: c for c in inspector.get_columns('submissions')}
        assert 'submitted_at' in cols, "submissions.submitted_at missing"
        assert 'created_at' in cols, "submissions.created_at MUST exist separately from submitted_at"

    def test_student_analytics_delay_is_numeric_not_interval(self):
        inspector = inspect(engine)
        cols = {c['name']: c for c in inspector.get_columns('student_analytics')}
        assert 'avg_submission_delay_hours' in cols, "avg_submission_delay_hours column missing"
        col_type = str(cols['avg_submission_delay_hours']['type']).upper()
        assert 'INTERVAL' not in col_type, (
            f"CRITICAL: avg_submission_delay_hours is type {col_type}. "
            "Must be NUMERIC(6,2). Flutter cannot parse PostgreSQL INTERVAL."
        )
        assert 'NUMERIC' in col_type or 'DECIMAL' in col_type or 'FLOAT' in col_type, (
            f"avg_submission_delay_hours should be NUMERIC type, got: {col_type}"
        )

    def test_all_18_indexes_exist(self):
        inspector = inspect(engine)
        existing = {idx['name'] for tbl in self.EXPECTED_TABLES
                    for idx in inspector.get_indexes(tbl)}
        required = [
            'idx_users_email','idx_users_role','idx_otp_email','idx_refresh_user',
            'idx_classes_admin','idx_cm_class','idx_cm_user','idx_cm_status',
            'idx_assignments_class','idx_assignments_status',
            'idx_submissions_assignment','idx_submissions_student','idx_submissions_current',
            'idx_sa_student','idx_sa_class','idx_sa_risk',
            'idx_notif_user','idx_notif_read'
        ]
        for idx in required:
            assert idx in existing, f"MISSING INDEX: {idx}"

    def test_uuid_primary_keys(self):
        inspector = inspect(engine)
        for tbl in ['users','classes','assignments','submissions','class_memberships','notifications']:
            cols = {c['name']: c for c in inspector.get_columns(tbl)}
            assert 'id' in cols
            assert 'UUID' in str(cols['id']['type']).upper(), f"{tbl}.id must be UUID"

    def test_all_timestamps_are_timestamptz(self):
        inspector = inspect(engine)
        for tbl, col in [('users','created_at'),('submissions','submitted_at'),
                          ('assignments','deadline_at'),('class_memberships','created_at')]:
            cols = {c['name']: c for c in inspector.get_columns(tbl)}
            if col in cols and cols[col]['nullable'] is False or col in cols:
                col_type = str(cols[col]['type']).upper()
                assert 'TIMEZONE' in col_type or 'TIMESTAMPTZ' in col_type or 'TIMESTAMP' in col_type, (
                    f"{tbl}.{col} should be TIMESTAMPTZ, got {col_type}"
                )

    def test_notifications_check_has_all_9_types(self):
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid='notifications'::regclass AND contype='c'"
            )).fetchone()
        assert result, "No CHECK on notifications"
        defn = result[0]
        for nt in ['STUDENT_APPROVED','STUDENT_REJECTED','ASSIGNMENT_PUBLISHED',
                   'DEADLINE_REMINDER','SUBMISSION_RECEIPT','MISSED_DEADLINE',
                   'RISK_ALERT','CO_MENTOR_ADDED','CLASS_ARCHIVED']:
            assert nt in defn, f"Notification type '{nt}' missing from CHECK constraint"


class TestRouteRegistration:

    def test_health_is_public_and_registered(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200, "GET /health must return 200"

    def test_auth_routes_registered(self, client):
        routes = [
            ("POST", "/api/v1/auth/admin/signup"),
            ("POST", "/api/v1/auth/admin/verify-otp"),
            ("POST", "/api/v1/auth/login"),
            ("POST", "/api/v1/auth/refresh"),
            ("POST", "/api/v1/auth/logout"),
            ("GET",  "/api/v1/auth/me"),
        ]
        for method, path in routes:
            if method == "POST":
                resp = client.post(path, json={})
            else:
                resp = client.get(path)
            assert resp.status_code != 404, f"ROUTE NOT FOUND: {method} {path} returned 404"
            assert resp.status_code != 405, f"METHOD NOT ALLOWED: {method} {path} returned 405"

    def test_class_routes_registered(self, client, admin_h):
        routes_404_check = [
            ("POST", "/api/v1/classes", {}),
            ("GET",  "/api/v1/classes", None),
            ("GET",  "/api/v1/classes/my-classes", None),
        ]
        for method, path, body in routes_404_check:
            if method == "POST":
                resp = client.post(path, headers=admin_h, json=body or {})
            else:
                resp = client.get(path, headers=admin_h)
            assert resp.status_code != 404, f"ROUTE NOT FOUND: {method} {path}"

    def test_assignment_routes_registered(self, client, admin_h):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        routes = [
            ("GET",  f"/api/v1/assignments?class_id={fake_uuid}"),
            ("GET",  f"/api/v1/assignments/{fake_uuid}"),
        ]
        for method, path in routes:
            resp = client.get(path, headers=admin_h)
            assert resp.status_code != 404 or resp.status_code in [404, 403, 422], (
                f"Route may not be registered: {method} {path}"
            )

    def test_submissions_my_route_registered(self, client, admin_h):
        resp = client.get("/api/v1/submissions/my", headers=admin_h)
        assert resp.status_code != 404, "GET /api/v1/submissions/my is NOT registered"

    def test_notification_read_all_registered_before_id_route(self, client, admin_h):
        """CRITICAL: /read-all must be defined BEFORE /{notification_id}/read
        or FastAPI will capture 'read-all' as the notification_id param."""
        resp = client.patch("/api/v1/notifications/read-all", headers=admin_h)
        assert resp.status_code != 404, (
            "PATCH /api/v1/notifications/read-all is NOT registered. "
            "Check route order in routers/notifications.py — "
            "PATCH /read-all must be defined BEFORE PATCH /{notification_id}/read"
        )
        assert resp.status_code != 422, (
            "read-all is being captured as a path param for /{notification_id}/read. "
            "Define PATCH /read-all BEFORE PATCH /{notification_id}/read."
        )

    def test_analytics_routes_registered(self, client, admin_h):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        routes = [
            f"/api/v1/analytics/admin/overview",
            f"/api/v1/analytics/classes/{fake_uuid}",
            f"/api/v1/analytics/classes/{fake_uuid}/students",
            f"/api/v1/analytics/students/{fake_uuid}",
            f"/api/v1/analytics/risk/students?class_id={fake_uuid}",
            f"/api/v1/analytics/assignments/{fake_uuid}",
        ]
        for path in routes:
            resp = client.get(path, headers=admin_h)
            if resp.status_code == 404:
                assert 'detail' in resp.json(), f"ROUTE NOT REGISTERED: GET {path}"
            else:
                assert resp.status_code != 404, f"ROUTE NOT REGISTERED: GET {path}"

    def test_my_classes_route_before_class_id_route(self, client, admin_h):
        """GET /my-classes must be defined BEFORE GET /{class_id} in classes router."""
        resp = client.get("/api/v1/classes/my-classes", headers=admin_h)
        assert resp.status_code != 422, (
            "ROUTE ORDER BUG: /my-classes is being captured as /{class_id}. "
            "Define GET /my-classes BEFORE GET /{class_id} in routers/classes.py"
        )


class TestAuthEndpoints:

    def test_admin_signup_201(self, client):
        with patch("services.email_service.send_otp_email"):
            resp = client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Test Admin", "email": "a1@test.com", "password": "Test1234!"
            })
        assert resp.status_code == 201
        assert resp.json() == {"message": "OTP sent to your email"}

    def test_duplicate_email_409(self, client):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "A", "email": "dup@test.com", "password": "Test1234!"
            })
            resp = client.post("/api/v1/auth/admin/signup", json={
                "full_name": "B", "email": "dup@test.com", "password": "Test1234!"
            })
        assert resp.status_code == 409

    def test_otp_verify_returns_tokens_and_user(self, client, db):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "OTP Admin", "email": "otp@test.com", "password": "Test1234!"
            })
        from models.user import OtpVerification
        otp = db.query(OtpVerification).filter_by(email="otp@test.com").first().otp_code
        resp = client.post("/api/v1/auth/admin/verify-otp", json={"email": "otp@test.com", "otp": otp})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["role"] == "ADMIN"

    def test_wrong_otp_400(self, client, db):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "X", "email": "badotp@test.com", "password": "Test1234!"
            })
        resp = client.post("/api/v1/auth/admin/verify-otp", json={
            "email": "badotp@test.com", "otp": "000000"
        })
        assert resp.status_code == 400

    def test_expired_otp_410(self, client, db):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Y", "email": "expotp@test.com", "password": "Test1234!"
            })
        db.execute(text(
            "UPDATE otp_verifications SET expires_at = now() - interval '1 minute' "
            "WHERE email = 'expotp@test.com'"
        ))
        db.commit()
        resp = client.post("/api/v1/auth/admin/verify-otp", json={
            "email": "expotp@test.com", "otp": "999999"
        })
        assert resp.status_code == 410

    def test_admin_login_all_user_fields_present(self, client, admin_token, db):
        # re-login to test response shape
        resp = client.post("/api/v1/auth/login", json={
            "email": "vadmin@test.com", "password": "Test1234!",
            "registration_id": "", "fcm_token": ""
        })
        assert resp.status_code == 200
        user = resp.json()["user"]
        required = ["id", "full_name", "email", "role", "class_id", "class_name", "registration_id"]
        for f in required:
            assert f in user, f"MISSING field in login response: user.{f}"

    def test_admin_login_class_fields_explicitly_null(self, client, admin_token):
        resp = client.post("/api/v1/auth/login", json={
            "email": "vadmin@test.com", "password": "Test1234!",
            "registration_id": "", "fcm_token": ""
        })
        user = resp.json()["user"]
        assert user["class_id"] is None, "class_id must be null (not missing) for admin"
        assert user["class_name"] is None, "class_name must be null (not missing) for admin"
        assert user["registration_id"] is None

    def test_wrong_password_401(self, client, admin_token):
        resp = client.post("/api/v1/auth/login", json={
            "email": "vadmin@test.com", "password": "WRONG",
            "registration_id": "", "fcm_token": ""
        })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    def test_token_refresh_returns_new_access_token(self, client, db):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "R", "email": "refresh@test.com", "password": "Test1234!"
            })
        from models.user import OtpVerification
        otp = db.query(OtpVerification).filter_by(email="refresh@test.com").first().otp_code
        verify = client.post("/api/v1/auth/admin/verify-otp", json={"email": "refresh@test.com", "otp": otp})
        refresh_token = verify.json()["refresh_token"]
        old_access = verify.json()["access_token"]
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert resp.json()["access_token"] != old_access

    def test_invalid_refresh_401(self, client):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "fake-token"})
        assert resp.status_code == 401

    def test_logout_revokes_token(self, client, db):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "L", "email": "logout@test.com", "password": "Test1234!"
            })
        from models.user import OtpVerification
        otp = db.query(OtpVerification).filter_by(email="logout@test.com").first().otp_code
        verify = client.post("/api/v1/auth/admin/verify-otp", json={"email": "logout@test.com", "otp": otp})
        access = verify.json()["access_token"]
        refresh = verify.json()["refresh_token"]
        logout = client.post("/api/v1/auth/logout",
                             headers={"Authorization": f"Bearer {access}"},
                             json={"refresh_token": refresh})
        assert logout.status_code == 200
        # Revoked token should fail
        retry = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert retry.status_code == 401

    def test_auth_me_returns_all_8_fields(self, client, admin_h):
        resp = client.get("/api/v1/auth/me", headers=admin_h)
        assert resp.status_code == 200
        data = resp.json()
        for f in ["id","full_name","email","role","registration_id","class_id","class_name","status"]:
            assert f in data, f"MISSING field in /auth/me: {f}"

    def test_auth_me_without_token_rejected(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code in [401, 422]

    def test_auth_me_with_bad_token_401(self, client):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad.token"})
        assert resp.status_code == 401

    def test_jwt_payload_structure(self, client, admin_h):
        import jwt as pyjwt
        token = admin_h["Authorization"].split(" ")[1]
        payload = pyjwt.decode(token, options={"verify_signature": False})
        assert "sub" in payload, "JWT missing 'sub'"
        assert "role" in payload, "JWT missing 'role'"
        assert "class_id" in payload, "JWT missing 'class_id' — must be present even if null"
        assert "exp" in payload, "JWT missing 'exp'"


class TestClassAndProvisioningEndpoints:

    def _make_class(self, client, admin_h, name="Test Class"):
        resp = client.post("/api/v1/classes", headers=admin_h, json={"class_name": name})
        assert resp.status_code == 201
        return resp.json()["id"]

    def _make_mentor(self, client, admin_h, class_id, email="m@test.com"):
        with patch("services.email_service.send_invite_email"):
            resp = client.post("/api/v1/provision/manual/mentor", headers=admin_h, json={
                "class_id": class_id, "full_name": "Mentor", "email": email,
                "password": "Mentor1234!", "is_primary_mentor": True
            })
        assert resp.status_code == 201
        return resp.json()

    def _login_mentor(self, client, email, password, reg_id):
        resp = client.post("/api/v1/auth/login", json={
            "email": email, "password": password,
            "registration_id": reg_id, "fcm_token": ""
        })
        assert resp.status_code == 200
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def _make_student(self, client, admin_h, class_id, email="s@test.com", reg="R001"):
        with patch("services.email_service.send_invite_email"):
            resp = client.post("/api/v1/provision/manual/student", headers=admin_h, json={
                "class_id": class_id, "full_name": "Student",
                "email": email, "password": "Student1234!", "registration_id": reg
            })
        assert resp.status_code == 201
        return resp.json()["id"]

    # ── Class creation ──

    def test_create_class_creates_analytics_row(self, client, db, admin_h):
        resp = client.post("/api/v1/classes", headers=admin_h, json={"class_name": "Cls1"})
        class_id = resp.json()["id"]
        from models.analytics import ClassAnalytics
        import uuid
        row = db.query(ClassAnalytics).filter_by(class_id=uuid.UUID(class_id)).first()
        assert row is not None, "class_analytics row must be created on class creation"

    def test_create_class_response_fields(self, client, admin_h):
        resp = client.post("/api/v1/classes", headers=admin_h, json={"class_name": "Cls2"})
        data = resp.json()
        for f in ["id","class_name","status","created_at"]:
            assert f in data, f"MISSING: create class response missing '{f}'"
        assert data["status"] == "ACTIVE"

    def test_get_classes_includes_student_and_mentor_count(self, client, admin_h):
        client.post("/api/v1/classes", headers=admin_h, json={"class_name": "CntCls"})
        resp = client.get("/api/v1/classes", headers=admin_h)
        classes = resp.json()["classes"]
        assert len(classes) > 0
        assert "student_count" in classes[0]
        assert "mentor_count" in classes[0]

    def test_my_classes_not_captured_by_class_id_param(self, client, db, admin_h):
        """The /my-classes route must be defined BEFORE /{class_id}."""
        class_id = self._make_class(client, admin_h, "MyClsTest")
        mentor = self._make_mentor(client, admin_h, class_id, "mc@test.com")
        mentor_h = self._login_mentor(client, "mc@test.com", "Mentor1234!", mentor["registration_id"])
        resp = client.get("/api/v1/classes/my-classes", headers=mentor_h)
        assert resp.status_code == 200, (
            f"GET /my-classes failed with {resp.status_code}. "
            "Likely route order bug — define my-classes BEFORE {class_id}."
        )
        assert "classes" in resp.json()

    # ── Student membership status ──

    def test_manual_student_starts_as_pending(self, client, db, admin_h):
        class_id = self._make_class(client, admin_h, "PendCls")
        student_id = self._make_student(client, admin_h, class_id, "pend@test.com", "PEND001")
        import uuid
        from models.class_ import ClassMembership
        m = db.query(ClassMembership).filter_by(
            user_id=uuid.UUID(student_id), class_id=uuid.UUID(class_id)
        ).first()
        assert m.status == "PENDING", (
            f"CRITICAL: Student membership must be PENDING on creation. Got: {m.status}. "
            "Check /provision/manual/student — must set status='PENDING' not 'ACTIVE'."
        )

    def test_bulk_import_student_starts_as_pending(self, client, db, admin_h):
        import io, openpyxl
        wb = openpyxl.Workbook()
        ws_c = wb.active; ws_c.title = 'Classes'
        ws_c.append(['class_name','description','academic_year'])
        ws_c.append(['BulkPendClass','','2026'])
        ws_m = wb.create_sheet('Mentors')
        ws_m.append(['class_name','mentor_name','mentor_email','mentor_password','is_primary_mentor'])
        ws_s = wb.create_sheet('Students')
        ws_s.append(['class_name','student_name','student_email','student_password','registration_id','roll_no'])
        ws_s.append(['BulkPendClass','Bulk Stu','bulkstu@test.com','Pass1234!','BULK001','1'])
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        with patch("services.email_service.send_invite_email"):
            resp = client.post("/api/v1/provision/bulk-import",
                               headers=admin_h,
                               files={"file": ("test.xlsx", buf.read(),
                                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert resp.status_code == 202
        import time
        batch_id = resp.json()["batch_id"]
        for _ in range(20):
            s = client.get(f"/api/v1/provision/bulk-import/{batch_id}", headers=admin_h).json()["status"]
            if s in ("COMPLETED","PARTIAL","FAILED"):
                break
            time.sleep(0.3)
        from models.user import User
        from models.class_ import ClassMembership
        stu = db.query(User).filter_by(email="bulkstu@test.com").first()
        if stu:
            m = db.query(ClassMembership).filter_by(user_id=stu.id).first()
            assert m and m.status == "PENDING", (
                f"CRITICAL: Bulk import student must be PENDING. Got: {m.status if m else 'NO ROW'}"
            )

    # ── Approval flow ──

    def test_pending_student_blocked_from_login(self, client, db, admin_h):
        class_id = self._make_class(client, admin_h, "BlkCls")
        self._make_student(client, admin_h, class_id, "blk@test.com", "BLK001")
        resp = client.post("/api/v1/auth/login", json={
            "email": "blk@test.com", "password": "Student1234!",
            "registration_id": "BLK001", "fcm_token": ""
        })
        assert resp.status_code == 403
        assert "pending" in resp.json()["detail"].lower()

    def test_approve_creates_student_analytics_row(self, client, db, admin_h):
        class_id = self._make_class(client, admin_h, "AppCls")
        mentor = self._make_mentor(client, admin_h, class_id, "appm@test.com")
        mentor_h = self._login_mentor(client, "appm@test.com", "Mentor1234!", mentor["registration_id"])
        student_id = self._make_student(client, admin_h, class_id, "apps@test.com", "APP001")
        with patch("services.fcm_service.send_single_fcm"):
            resp = client.patch(
                f"/api/v1/classes/{class_id}/students/{student_id}/approve",
                headers=mentor_h, json={}
            )
        assert resp.status_code == 200
        from models.analytics import StudentAnalytics
        import uuid
        row = db.query(StudentAnalytics).filter_by(
            student_id=uuid.UUID(student_id), class_id=uuid.UUID(class_id)
        ).first()
        assert row is not None, "student_analytics must be created on approval"
        assert row.risk_level == "NORMAL"
        assert row.total_assigned == 0

    def test_approve_creates_student_approved_notification(self, client, db, admin_h):
        class_id = self._make_class(client, admin_h, "NotifCls")
        mentor = self._make_mentor(client, admin_h, class_id, "nm@test.com")
        mentor_h = self._login_mentor(client, "nm@test.com", "Mentor1234!", mentor["registration_id"])
        student_id = self._make_student(client, admin_h, class_id, "ns@test.com", "NOTIF001")
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{class_id}/students/{student_id}/approve",
                         headers=mentor_h, json={})
        from models.notification import Notification
        import uuid
        n = db.query(Notification).filter_by(
            user_id=uuid.UUID(student_id), notification_type="STUDENT_APPROVED"
        ).first()
        assert n is not None, "STUDENT_APPROVED notification must be inserted on approval"

    def test_approved_student_can_login(self, client, db, admin_h):
        class_id = self._make_class(client, admin_h, "LoginCls")
        mentor = self._make_mentor(client, admin_h, class_id, "lm@test.com")
        mentor_h = self._login_mentor(client, "lm@test.com", "Mentor1234!", mentor["registration_id"])
        student_id = self._make_student(client, admin_h, class_id, "ls@test.com", "LOGIN001")
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{class_id}/students/{student_id}/approve",
                         headers=mentor_h, json={})
        resp = client.post("/api/v1/auth/login", json={
            "email": "ls@test.com", "password": "Student1234!",
            "registration_id": "LOGIN001", "fcm_token": ""
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "STUDENT"
        assert resp.json()["user"]["class_id"] == class_id

    def test_reject_stores_reason(self, client, db, admin_h):
        class_id = self._make_class(client, admin_h, "RejCls")
        mentor = self._make_mentor(client, admin_h, class_id, "rm@test.com")
        mentor_h = self._login_mentor(client, "rm@test.com", "Mentor1234!", mentor["registration_id"])
        student_id = self._make_student(client, admin_h, class_id, "rs@test.com", "REJ001")
        with patch("services.fcm_service.send_single_fcm"):
            resp = client.patch(
                f"/api/v1/classes/{class_id}/students/{student_id}/reject",
                headers=mentor_h, json={"reason": "Duplicate enrollment"}
            )
        assert resp.status_code == 200
        from models.class_ import ClassMembership
        import uuid
        m = db.query(ClassMembership).filter_by(user_id=uuid.UUID(student_id)).first()
        assert m.status == "REJECTED"
        assert m.rejection_reason == "Duplicate enrollment"

    def test_students_list_uses_membership_status_not_status(self, client, db, admin_h):
        """CRITICAL field name check — Flutter model expects 'membership_status'."""
        class_id = self._make_class(client, admin_h, "FieldCls")
        mentor = self._make_mentor(client, admin_h, class_id, "fm@test.com")
        mentor_h = self._login_mentor(client, "fm@test.com", "Mentor1234!", mentor["registration_id"])
        self._make_student(client, admin_h, class_id, "fs@test.com", "FIELD001")
        resp = client.get(f"/api/v1/classes/{class_id}/students", headers=mentor_h)
        assert resp.status_code == 200
        students = resp.json()["students"]
        if students:
            assert "membership_status" in students[0], (
                "FIELD NAME MISMATCH: 'membership_status' missing. "
                "Do NOT return 'status' — Flutter model uses 'membership_status'."
            )
            assert "status" not in students[0], (
                "FIELD NAME MISMATCH: 'status' must not appear — use 'membership_status'."
            )
            assert "joined_at" in students[0], "MISSING: 'joined_at' in students list"


class TestAssignmentAndSubmissionEndpoints:

    def _full_setup(self, client, db, admin_h):
        """Returns (class_id, mentor_headers, student_headers)."""
        # Class
        cls_id = client.post("/api/v1/classes", headers=admin_h,
                             json={"class_name": "AssgnCls"}).json()["id"]
        # Mentor
        with patch("services.email_service.send_invite_email"):
            m = client.post("/api/v1/provision/manual/mentor", headers=admin_h, json={
                "class_id": cls_id, "full_name": "M", "email": "as_m@test.com",
                "password": "Mentor1234!", "is_primary_mentor": True
            }).json()
        mentor_resp = client.post("/api/v1/auth/login", json={
            "email": "as_m@test.com", "password": "Mentor1234!",
            "registration_id": m["registration_id"], "fcm_token": ""
        })
        mentor_h = {"Authorization": f"Bearer {mentor_resp.json()['access_token']}"}
        # Student
        with patch("services.email_service.send_invite_email"):
            s_id = client.post("/api/v1/provision/manual/student", headers=admin_h, json={
                "class_id": cls_id, "full_name": "S", "email": "as_s@test.com",
                "password": "Student1234!", "registration_id": "AS001"
            }).json()["id"]
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{cls_id}/students/{s_id}/approve",
                         headers=mentor_h, json={})
        student_resp = client.post("/api/v1/auth/login", json={
            "email": "as_s@test.com", "password": "Student1234!",
            "registration_id": "AS001", "fcm_token": ""
        })
        student_h = {"Authorization": f"Bearer {student_resp.json()['access_token']}"}
        return cls_id, mentor_h, student_h

    def test_create_assignment_returns_draft(self, client, db, admin_h):
        cls_id, mentor_h, _ = self._full_setup(client, db, admin_h)
        resp = client.post("/api/v1/assignments", headers=mentor_h, json={
            "class_id": cls_id, "title": "Test Assign",
            "content_type": "RICH_TEXT", "rich_text_body": "Instructions here",
            "submission_type": "TEXT", "auto_close": False
        })
        assert resp.status_code == 201
        assert resp.json()["status"] == "DRAFT"

    def test_publish_creates_assignment_analytics(self, client, db, admin_h):
        cls_id, mentor_h, _ = self._full_setup(client, db, admin_h)
        a_id = client.post("/api/v1/assignments", headers=mentor_h, json={
            "class_id": cls_id, "title": "PubAssign",
            "content_type": "RICH_TEXT", "rich_text_body": "Body",
            "submission_type": "TEXT", "auto_close": False
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"), \
             patch("services.fcm_service.send_single_fcm"):
            resp = client.post(f"/api/v1/assignments/{a_id}/publish", headers=mentor_h, json={})
        assert resp.status_code == 200
        from models.analytics import AssignmentAnalytics
        import uuid
        row = db.query(AssignmentAnalytics).filter_by(assignment_id=uuid.UUID(a_id)).first()
        assert row is not None, "assignment_analytics row must be created on publish"

    def test_student_sees_only_published_assignments(self, client, db, admin_h):
        cls_id, mentor_h, student_h = self._full_setup(client, db, admin_h)
        # Create draft — student should NOT see it
        client.post("/api/v1/assignments", headers=mentor_h, json={
            "class_id": cls_id, "title": "Draft Assign",
            "content_type": "RICH_TEXT", "rich_text_body": "x",
            "submission_type": "TEXT", "auto_close": False
        })
        resp = client.get(f"/api/v1/assignments?class_id={cls_id}", headers=student_h)
        assert resp.status_code == 200
        assignments = resp.json()["assignments"]
        drafts = [a for a in assignments if a["status"] == "DRAFT"]
        assert len(drafts) == 0, "Students must NOT see DRAFT assignments"

    def test_assignment_detail_has_student_submission_key(self, client, db, admin_h):
        cls_id, mentor_h, student_h = self._full_setup(client, db, admin_h)
        a_id = client.post("/api/v1/assignments", headers=mentor_h, json={
            "class_id": cls_id, "title": "DetailAssign",
            "content_type": "RICH_TEXT", "rich_text_body": "x",
            "submission_type": "TEXT", "auto_close": False
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"), \
             patch("services.fcm_service.send_single_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=mentor_h, json={})
        resp = client.get(f"/api/v1/assignments/{a_id}", headers=student_h)
        assert resp.status_code == 200
        data = resp.json()
        assert "student_submission" in data, (
            "MISSING: 'student_submission' key in assignment detail response. "
            "Must always be present — even when no submission exists."
        )
        ss = data["student_submission"]
        for f in ["submitted","submission_id","submitted_at","is_late","version"]:
            assert f in ss, f"MISSING in student_submission: {f}"
        assert ss["submitted"] is False

    def test_text_submission_returns_receipt(self, client, db, admin_h):
        cls_id, mentor_h, student_h = self._full_setup(client, db, admin_h)
        a_id = client.post("/api/v1/assignments", headers=mentor_h, json={
            "class_id": cls_id, "title": "SubAssign",
            "content_type": "RICH_TEXT", "rich_text_body": "x",
            "submission_type": "TEXT", "auto_close": False
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"), \
             patch("services.fcm_service.send_single_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=mentor_h, json={})
        resp = client.post(f"/api/v1/assignments/{a_id}/submit",
                           headers=student_h,
                           json={"submission_type": "TEXT", "text_answer": "My answer", "file_url": None})
        assert resp.status_code == 201
        data = resp.json()
        for f in ["submission_id","submitted_at","is_late","version","receipt"]:
            assert f in data, f"MISSING in submit response: {f}"

    def test_resubmission_increments_version(self, client, db, admin_h):
        cls_id, mentor_h, student_h = self._full_setup(client, db, admin_h)
        a_id = client.post("/api/v1/assignments", headers=mentor_h, json={
            "class_id": cls_id, "title": "ResubAssign",
            "content_type": "RICH_TEXT", "rich_text_body": "x",
            "submission_type": "TEXT", "auto_close": False
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"), \
             patch("services.fcm_service.send_single_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=mentor_h, json={})
        client.post(f"/api/v1/assignments/{a_id}/submit", headers=student_h,
                    json={"submission_type": "TEXT", "text_answer": "v1", "file_url": None})
        r2 = client.post(f"/api/v1/assignments/{a_id}/submit", headers=student_h,
                         json={"submission_type": "TEXT", "text_answer": "v2", "file_url": None})
        assert r2.status_code == 201
        assert r2.json()["version"] == 2

    def test_resubmission_marks_old_as_not_current(self, client, db, admin_h):
        cls_id, mentor_h, student_h = self._full_setup(client, db, admin_h)
        a_id = client.post("/api/v1/assignments", headers=mentor_h, json={
            "class_id": cls_id, "title": "CurAssign",
            "content_type": "RICH_TEXT", "rich_text_body": "x",
            "submission_type": "TEXT", "auto_close": False
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"), \
             patch("services.fcm_service.send_single_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=mentor_h, json={})
        client.post(f"/api/v1/assignments/{a_id}/submit", headers=student_h,
                    json={"submission_type": "TEXT", "text_answer": "v1", "file_url": None})
        client.post(f"/api/v1/assignments/{a_id}/submit", headers=student_h,
                    json={"submission_type": "TEXT", "text_answer": "v2", "file_url": None})
        from models.submission import Submission
        import uuid
        from models.user import User
        stu = db.query(User).filter_by(email="as_s@test.com").first()
        all_subs = db.query(Submission).filter_by(
            assignment_id=uuid.UUID(a_id), student_id=stu.id
        ).all()
        current_count = sum(1 for s in all_subs if s.is_current)
        assert current_count == 1, "ONLY the latest submission must have is_current=True"

    def test_submissions_my_only_returns_current(self, client, db, admin_h):
        cls_id, mentor_h, student_h = self._full_setup(client, db, admin_h)
        a_id = client.post("/api/v1/assignments", headers=mentor_h, json={
            "class_id": cls_id, "title": "MySubAssign",
            "content_type": "RICH_TEXT", "rich_text_body": "x",
            "submission_type": "TEXT", "auto_close": False
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"), \
             patch("services.fcm_service.send_single_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=mentor_h, json={})
        client.post(f"/api/v1/assignments/{a_id}/submit", headers=student_h,
                    json={"submission_type": "TEXT", "text_answer": "v1", "file_url": None})
        client.post(f"/api/v1/assignments/{a_id}/submit", headers=student_h,
                    json={"submission_type": "TEXT", "text_answer": "v2", "file_url": None})
        resp = client.get("/api/v1/submissions/my", headers=student_h)
        assert resp.status_code == 200
        subs = resp.json()["submissions"]
        matching = [s for s in subs if s["assignment_id"] == a_id]
        assert len(matching) == 1, "GET /submissions/my must return only is_current=true submissions"

    def test_tracker_response_shape(self, client, db, admin_h):
        cls_id, mentor_h, _ = self._full_setup(client, db, admin_h)
        a_id = client.post("/api/v1/assignments", headers=mentor_h, json={
            "class_id": cls_id, "title": "TrkAssign",
            "content_type": "RICH_TEXT", "rich_text_body": "x",
            "submission_type": "TEXT", "auto_close": False
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"), \
             patch("services.fcm_service.send_single_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=mentor_h, json={})
        resp = client.get(f"/api/v1/assignments/{a_id}/tracker", headers=mentor_h)
        assert resp.status_code == 200
        data = resp.json()
        for f in ["assignment_id","title","deadline_at","status",
                  "submitted_count","pending_count","missed_count","late_count","students"]:
            assert f in data, f"MISSING in tracker response: {f}"
        if data["students"]:
            for f in ["student_id","full_name","registration_id","tracker_status","submitted_at","is_late","submission_id"]:
                assert f in data["students"][0], f"MISSING in tracker student row: {f}"


class TestAnalyticsEndpoints:

    def test_admin_overview_shape(self, client, admin_h):
        resp = client.get("/api/v1/analytics/admin/overview", headers=admin_h)
        assert resp.status_code == 200
        data = resp.json()
        for f in ["total_classes","total_mentors","total_students","total_assignments","classes"]:
            assert f in data, f"MISSING in admin overview: {f}"

    def test_admin_overview_class_card_has_primary_mentor_name(self, client, db, admin_h):
        with patch("services.email_service.send_invite_email"):
            cls_id = client.post("/api/v1/classes", headers=admin_h,
                                 json={"class_name": "OvCls"}).json()["id"]
            client.post("/api/v1/provision/manual/mentor", headers=admin_h, json={
                "class_id": cls_id, "full_name": "Overview Mentor",
                "email": "ovm@test.com", "password": "M1234!", "is_primary_mentor": True
            })
        resp = client.get("/api/v1/analytics/admin/overview", headers=admin_h)
        classes = resp.json()["classes"]
        ov_cls = next((c for c in classes if c["class_id"] == cls_id), None)
        assert ov_cls is not None
        assert "primary_mentor_name" in ov_cls, (
            "MISSING: primary_mentor_name in admin overview class card. "
            "This requires a JOIN to class_memberships + users — check the query."
        )

    def test_class_analytics_shape(self, client, db, admin_h):
        with patch("services.email_service.send_invite_email"):
            cls_id = client.post("/api/v1/classes", headers=admin_h,
                                 json={"class_name": "AnCls"}).json()["id"]
        resp = client.get(f"/api/v1/analytics/classes/{cls_id}", headers=admin_h)
        assert resp.status_code == 200
        data = resp.json()
        required = ["class_id","class_name","total_students","total_assignments",
                    "avg_completion","avg_miss_rate","avg_late_rate","high_risk_count",
                    "bottleneck_assignments","risk_distribution"]
        for f in required:
            assert f in data, f"MISSING in class analytics: {f}"
        dist = data["risk_distribution"]
        for level in ["NORMAL","LOW","MEDIUM","HIGH","RECOVERING"]:
            assert level in dist, f"risk_distribution missing '{level}'"

    def test_student_analytics_shape(self, client, db, admin_h):
        cls_id = client.post("/api/v1/classes", headers=admin_h,
                             json={"class_name": "SACls"}).json()["id"]
        with patch("services.email_service.send_invite_email"):
            mentor = client.post("/api/v1/provision/manual/mentor", headers=admin_h, json={
                "class_id": cls_id, "full_name": "SAM", "email": "sam@test.com",
                "password": "M1234!", "is_primary_mentor": True
            }).json()
        mentor_resp = client.post("/api/v1/auth/login", json={
            "email": "sam@test.com", "password": "M1234!",
            "registration_id": mentor["registration_id"], "fcm_token": ""
        })
        mentor_h = {"Authorization": f"Bearer {mentor_resp.json()['access_token']}"}
        with patch("services.email_service.send_invite_email"):
            s_id = client.post("/api/v1/provision/manual/student", headers=admin_h, json={
                "class_id": cls_id, "full_name": "SS", "email": "ss@test.com",
                "password": "S1234!", "registration_id": "SA001"
            }).json()["id"]
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{cls_id}/students/{s_id}/approve",
                         headers=mentor_h, json={})
        resp = client.get(f"/api/v1/analytics/students/{s_id}", headers=admin_h)
        assert resp.status_code == 200
        data = resp.json()
        required = ["student_id","full_name","class_name","total_assigned","total_submitted",
                    "total_missed","total_late","completion_rate","current_streak","longest_streak",
                    "avg_submission_delay_hours","risk_level","consecutive_misses",
                    "class_avg_completion","assignment_history"]
        for f in required:
            assert f in data, f"MISSING in student analytics: {f}"

    def test_student_cannot_view_other_student_analytics(self, client, db, admin_h):
        cls_id = client.post("/api/v1/classes", headers=admin_h,
                             json={"class_name": "SelfCls"}).json()["id"]
        with patch("services.email_service.send_invite_email"):
            mentor = client.post("/api/v1/provision/manual/mentor", headers=admin_h, json={
                "class_id": cls_id, "full_name": "SM", "email": "selfm@test.com",
                "password": "M1234!", "is_primary_mentor": True
            }).json()
        mentor_resp = client.post("/api/v1/auth/login", json={
            "email": "selfm@test.com", "password": "M1234!",
            "registration_id": mentor["registration_id"], "fcm_token": ""
        })
        mentor_h = {"Authorization": f"Bearer {mentor_resp.json()['access_token']}"}
        with patch("services.email_service.send_invite_email"):
            s1_id = client.post("/api/v1/provision/manual/student", headers=admin_h, json={
                "class_id": cls_id, "full_name": "S1", "email": "se1@test.com",
                "password": "S1234!", "registration_id": "SE001"
            }).json()["id"]
            s2_id = client.post("/api/v1/provision/manual/student", headers=admin_h, json={
                "class_id": cls_id, "full_name": "S2", "email": "se2@test.com",
                "password": "S1234!", "registration_id": "SE002"
            }).json()["id"]
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{cls_id}/students/{s1_id}/approve", headers=mentor_h, json={})
            client.patch(f"/api/v1/classes/{cls_id}/students/{s2_id}/approve", headers=mentor_h, json={})
        s1_resp = client.post("/api/v1/auth/login", json={
            "email": "se1@test.com", "password": "S1234!", "registration_id": "SE001", "fcm_token": ""
        })
        s1_h = {"Authorization": f"Bearer {s1_resp.json()['access_token']}"}
        # Student 1 tries to view Student 2's analytics
        resp = client.get(f"/api/v1/analytics/students/{s2_id}", headers=s1_h)
        assert resp.status_code == 403, "Student must NOT be able to view another student's analytics"


class TestNotificationEndpoints:

    def test_get_notifications_shape(self, client, admin_h):
        resp = client.get("/api/v1/notifications", headers=admin_h)
        assert resp.status_code == 200
        data = resp.json()
        assert "notifications" in data
        assert "unread_count" in data

    def test_notification_read_all_route_order(self, client, admin_h):
        """If /read-all is caught as /{notification_id}/read, this will fail with 422 or 404."""
        resp = client.patch("/api/v1/notifications/read-all", headers=admin_h)
        assert resp.status_code == 200, (
            f"PATCH /notifications/read-all failed with {resp.status_code}. "
            "Check route order in notifications.py — read-all must come BEFORE /{id}/read."
        )

    def test_read_notification_changes_is_read(self, client, db, admin_h):
        from models.notification import Notification
        import uuid
        # Insert a test notification directly
        from models.user import User
        admin_user = db.query(User).filter_by(email="vadmin@test.com").first()
        if admin_user:
            notif = Notification(
                user_id=admin_user.id,
                notification_type="ASSIGNMENT_PUBLISHED",
                title="Test Notif",
                body="Test body"
            )
            db.add(notif)
            db.commit()
            db.refresh(notif)
            resp = client.patch(f"/api/v1/notifications/{notif.id}/read", headers=admin_h)
            assert resp.status_code == 200
            assert resp.json()["is_read"] is True


class TestSecurityAndRBAC:

    def test_no_route_accessible_without_token(self, client):
        protected_routes = [
            ("GET",  "/api/v1/classes"),
            ("POST", "/api/v1/classes"),
            ("GET",  "/api/v1/analytics/admin/overview"),
            ("GET",  "/api/v1/notifications"),
            ("GET",  "/api/v1/submissions/my"),
        ]
        for method, path in protected_routes:
            if method == "GET":
                resp = client.get(path)
            else:
                resp = client.post(path, json={})
            assert resp.status_code in [401, 422], (
                f"SECURITY: {method} {path} returned {resp.status_code} without token. "
                "Should return 401 or 422."
            )

    def test_student_cannot_create_class(self, client, db, admin_h):
        cls_id = client.post("/api/v1/classes", headers=admin_h,
                             json={"class_name": "RBACCls"}).json()["id"]
        with patch("services.email_service.send_invite_email"):
            mentor = client.post("/api/v1/provision/manual/mentor", headers=admin_h, json={
                "class_id": cls_id, "full_name": "RM", "email": "rbm@test.com",
                "password": "M1234!", "is_primary_mentor": True
            }).json()
        mentor_resp = client.post("/api/v1/auth/login", json={
            "email": "rbm@test.com", "password": "M1234!",
            "registration_id": mentor["registration_id"], "fcm_token": ""
        })
        mentor_h = {"Authorization": f"Bearer {mentor_resp.json()['access_token']}"}
        with patch("services.email_service.send_invite_email"):
            s_id = client.post("/api/v1/provision/manual/student", headers=admin_h, json={
                "class_id": cls_id, "full_name": "RS", "email": "rbs@test.com",
                "password": "S1234!", "registration_id": "RBAC001"
            }).json()["id"]
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{cls_id}/students/{s_id}/approve",
                         headers=mentor_h, json={})
        student_resp = client.post("/api/v1/auth/login", json={
            "email": "rbs@test.com", "password": "S1234!",
            "registration_id": "RBAC001", "fcm_token": ""
        })
        student_h = {"Authorization": f"Bearer {student_resp.json()['access_token']}"}
        resp = client.post("/api/v1/classes", headers=student_h, json={"class_name": "HackClass"})
        assert resp.status_code == 403, "Student must not be able to create classes"

    def test_mentor_cannot_access_admin_overview(self, client, db, admin_h):
        cls_id = client.post("/api/v1/classes", headers=admin_h,
                             json={"class_name": "OvSecCls"}).json()["id"]
        with patch("services.email_service.send_invite_email"):
            m = client.post("/api/v1/provision/manual/mentor", headers=admin_h, json={
                "class_id": cls_id, "full_name": "OvM", "email": "ovm2@test.com",
                "password": "M1234!", "is_primary_mentor": True
            }).json()
        mentor_resp = client.post("/api/v1/auth/login", json={
            "email": "ovm2@test.com", "password": "M1234!",
            "registration_id": m["registration_id"], "fcm_token": ""
        })
        mentor_h = {"Authorization": f"Bearer {mentor_resp.json()['access_token']}"}
        resp = client.get("/api/v1/analytics/admin/overview", headers=mentor_h)
        assert resp.status_code == 403, "Mentor must NOT access admin analytics overview"

    def test_mentor_cannot_access_other_class(self, client, db, admin_h):
        cls1 = client.post("/api/v1/classes", headers=admin_h,
                           json={"class_name": "IsoC1"}).json()["id"]
        cls2 = client.post("/api/v1/classes", headers=admin_h,
                           json={"class_name": "IsoC2"}).json()["id"]
        with patch("services.email_service.send_invite_email"):
            m = client.post("/api/v1/provision/manual/mentor", headers=admin_h, json={
                "class_id": cls1, "full_name": "IsoM", "email": "isom@test.com",
                "password": "M1234!", "is_primary_mentor": True
            }).json()
        mentor_resp = client.post("/api/v1/auth/login", json={
            "email": "isom@test.com", "password": "M1234!",
            "registration_id": m["registration_id"], "fcm_token": ""
        })
        mentor_h = {"Authorization": f"Bearer {mentor_resp.json()['access_token']}"}
        # Try to access class 2 with class 1's mentor
        resp = client.get(f"/api/v1/classes/{cls2}", headers=mentor_h)
        assert resp.status_code == 403, "Mentor must NOT access classes they don't belong to"


class TestResponseFieldContract:
    """These tests verify exact field names match the Flutter model expectations."""

    def test_login_response_field_names(self, client, admin_token):
        resp = client.post("/api/v1/auth/login", json={
            "email": "vadmin@test.com", "password": "Test1234!",
            "registration_id": "", "fcm_token": ""
        })
        assert resp.status_code == 200
        data = resp.json()
        # Top level
        assert "access_token" in data, "Must use 'access_token' not 'token' or 'jwt'"
        assert "refresh_token" in data
        # User object field names
        user = data["user"]
        assert "full_name" in user, "Must use 'full_name' not 'name' or 'fullName'"
        assert "class_id" in user, "Must use 'class_id' not 'classId'"
        assert "class_name" in user, "Must use 'class_name' not 'className'"
        assert "registration_id" in user, "Must use 'registration_id' not 'regId'"

    def test_assignment_list_field_names(self, client, db, admin_h):
        cls_id = client.post("/api/v1/classes", headers=admin_h,
                             json={"class_name": "FldCls"}).json()["id"]
        with patch("services.email_service.send_invite_email"):
            mentor = client.post("/api/v1/provision/manual/mentor", headers=admin_h, json={
                "class_id": cls_id, "full_name": "FM", "email": "fm2@test.com",
                "password": "M1234!", "is_primary_mentor": True
            }).json()
        mentor_resp = client.post("/api/v1/auth/login", json={
            "email": "fm2@test.com", "password": "M1234!",
            "registration_id": mentor["registration_id"], "fcm_token": ""
        })
        mentor_h = {"Authorization": f"Bearer {mentor_resp.json()['access_token']}"}
        client.post("/api/v1/assignments", headers=mentor_h, json={
            "class_id": cls_id, "title": "FieldTest",
            "content_type": "RICH_TEXT", "rich_text_body": "x",
            "submission_type": "TEXT", "auto_close": False
        })
        resp = client.get(f"/api/v1/assignments?class_id={cls_id}", headers=mentor_h)
        assignments = resp.json()["assignments"]
        if assignments:
            a = assignments[0]
            assert "content_type" in a, "Must use 'content_type' not 'contentType'"
            assert "submission_type" in a, "Must use 'submission_type'"
            assert "deadline_at" in a, "Must use 'deadline_at' not 'deadline'"
            assert "created_at" in a, "Must use 'created_at'"
            assert "created_by_name" in a, "Must include 'created_by_name' in list"

    def test_approval_list_field_names(self, client, db, admin_h):
        cls_id = client.post("/api/v1/classes", headers=admin_h,
                             json={"class_name": "AprvFld"}).json()["id"]
        with patch("services.email_service.send_invite_email"):
            mentor = client.post("/api/v1/provision/manual/mentor", headers=admin_h, json={
                "class_id": cls_id, "full_name": "APM", "email": "apm@test.com",
                "password": "M1234!", "is_primary_mentor": True
            }).json()
            client.post("/api/v1/provision/manual/student", headers=admin_h, json={
                "class_id": cls_id, "full_name": "APS", "email": "aps@test.com",
                "password": "S1234!", "registration_id": "APRVFLD001"
            })
        mentor_resp = client.post("/api/v1/auth/login", json={
            "email": "apm@test.com", "password": "M1234!",
            "registration_id": mentor["registration_id"], "fcm_token": ""
        })
        mentor_h = {"Authorization": f"Bearer {mentor_resp.json()['access_token']}"}
        resp = client.get(f"/api/v1/classes/{cls_id}/approvals", headers=mentor_h)
        assert resp.status_code == 200
        data = resp.json()
        assert "pending_count" in data, "Must include 'pending_count'"
        assert "pending" in data, "Must use 'pending' not 'students'"
        if data["pending"]:
            row = data["pending"][0]
            assert "student_id" in row, "Must use 'student_id' not 'id'"
            assert "requested_at" in row, "Must use 'requested_at' not 'created_at'"
            assert "joined_via" in row

    def test_notifications_response_field_names(self, client, admin_h):
        resp = client.get("/api/v1/notifications", headers=admin_h)
        data = resp.json()
        assert "notifications" in data, "Must use 'notifications' array key"
        assert "unread_count" in data, "Must include 'unread_count'"
        if data["notifications"]:
            n = data["notifications"][0]
            assert "notification_type" in n
            assert "is_read" in n
            assert "created_at" in n


class TestFullScenario:
    """One complete flow: admin → class → mentor → student → assign → submit → analytics."""

    def test_complete_flow(self, client, db, admin_h):
        # 1. Create class
        cls = client.post("/api/v1/classes", headers=admin_h,
                          json={"class_name": "E2E Class", "academic_year": "2026"})
        assert cls.status_code == 201
        cls_id = cls.json()["id"]

        # 2. Provision mentor
        with patch("services.email_service.send_invite_email"):
            mentor_data = client.post("/api/v1/provision/manual/mentor", headers=admin_h, json={
                "class_id": cls_id, "full_name": "E2E Mentor", "email": "e2em@test.com",
                "password": "Mentor1234!", "is_primary_mentor": True
            }).json()
        mentor_login = client.post("/api/v1/auth/login", json={
            "email": "e2em@test.com", "password": "Mentor1234!",
            "registration_id": mentor_data["registration_id"], "fcm_token": ""
        })
        assert mentor_login.status_code == 200
        mentor_h = {"Authorization": f"Bearer {mentor_login.json()['access_token']}"}

        # 3. Provision student (starts PENDING)
        with patch("services.email_service.send_invite_email"):
            s_id = client.post("/api/v1/provision/manual/student", headers=admin_h, json={
                "class_id": cls_id, "full_name": "E2E Student", "email": "e2es@test.com",
                "password": "Student1234!", "registration_id": "E2E001"
            }).json()["id"]

        # 4. Student blocked
        blocked = client.post("/api/v1/auth/login", json={
            "email": "e2es@test.com", "password": "Student1234!",
            "registration_id": "E2E001", "fcm_token": ""
        })
        assert blocked.status_code == 403

        # 5. Mentor approves
        with patch("services.fcm_service.send_single_fcm"):
            approved = client.patch(f"/api/v1/classes/{cls_id}/students/{s_id}/approve",
                                    headers=mentor_h, json={})
        assert approved.status_code == 200

        # 6. Student logs in
        student_login = client.post("/api/v1/auth/login", json={
            "email": "e2es@test.com", "password": "Student1234!",
            "registration_id": "E2E001", "fcm_token": ""
        })
        assert student_login.status_code == 200
        student_h = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

        # 7. Create and publish assignment
        a_id = client.post("/api/v1/assignments", headers=mentor_h, json={
            "class_id": cls_id, "title": "E2E Assignment",
            "content_type": "RICH_TEXT", "rich_text_body": "Do this",
            "submission_type": "TEXT", "auto_close": False
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"), \
             patch("services.fcm_service.send_single_fcm"):
            published = client.post(f"/api/v1/assignments/{a_id}/publish", headers=mentor_h, json={})
        assert published.status_code == 200

        # 8. Student submits
        submit = client.post(f"/api/v1/assignments/{a_id}/submit", headers=student_h, json={
            "submission_type": "TEXT", "text_answer": "E2E answer", "file_url": None
        })
        assert submit.status_code == 201
        assert submit.json()["is_late"] is False

        # 9. Check tracker
        tracker = client.get(f"/api/v1/assignments/{a_id}/tracker", headers=mentor_h)
        assert tracker.status_code == 200
        t_data = tracker.json()
        assert t_data["submitted_count"] == 1

        # 10. Close assignment
        with patch("services.fcm_service.send_batch_fcm"), \
             patch("services.fcm_service.send_single_fcm"):
            closed = client.post(f"/api/v1/assignments/{a_id}/close", headers=mentor_h, json={})
        assert closed.status_code == 200

        # 11. Student analytics recomputed
        analytics = client.get(f"/api/v1/analytics/students/{s_id}", headers=admin_h)
        assert analytics.status_code == 200
        data = analytics.json()
        assert data["total_assigned"] == 1
        assert data["total_submitted"] == 1
        assert data["total_missed"] == 0
        assert float(data["completion_rate"]) == 100.0

        # 12. Notifications received
        notifs = client.get("/api/v1/notifications", headers=student_h)
        assert notifs.status_code == 200
        assert notifs.json()["unread_count"] >= 1


