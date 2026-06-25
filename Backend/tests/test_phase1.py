import pytest
from sqlalchemy import inspect, text
from database import engine


class TestDatabaseTables:

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

    def test_users_table_columns(self):
        inspector = inspect(engine)
        cols = {c['name']: c for c in inspector.get_columns('users')}
        required = ['id', 'role', 'full_name', 'email', 'password_hash',
                    'registration_id', 'status', 'fcm_token', 'created_at', 'updated_at']
        for col in required:
            assert col in cols, f"MISSING COLUMN users.{col}"

    def test_class_memberships_columns(self):
        inspector = inspect(engine)
        cols = {c['name'] for c in inspector.get_columns('class_memberships')}
        required = ['id', 'class_id', 'user_id', 'member_role', 'is_primary_mentor',
                    'joined_via', 'status', 'rejection_reason', 'created_at', 'updated_at']
        for col in required:
            assert col in cols, f"MISSING COLUMN class_memberships.{col}"

    def test_submissions_has_required_columns(self):
        inspector = inspect(engine)
        cols = {c['name'] for c in inspector.get_columns('submissions')}
        assert 'submitted_at' in cols
        assert 'is_current' in cols
        assert 'version' in cols

    def test_student_analytics_uses_numeric_not_interval(self):
        inspector = inspect(engine)
        cols = {c['name']: c for c in inspector.get_columns('student_analytics')}
        assert 'avg_submission_delay_hours' in cols
        col_type = str(cols['avg_submission_delay_hours']['type']).upper()
        assert 'INTERVAL' not in col_type, "avg_submission_delay_hours must be NUMERIC not INTERVAL"

    def test_class_memberships_status_check_includes_pending(self):
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = 'class_memberships'::regclass AND contype = 'c'
                AND pg_get_constraintdef(oid) ILIKE '%status%'
            """)).fetchone()
        assert result is not None
        assert 'PENDING' in result[0]
        assert 'REJECTED' in result[0]

    def test_all_pk_are_uuid(self):
        inspector = inspect(engine)
        tables = ['users', 'classes', 'assignments', 'submissions', 'class_memberships', 'notifications']
        for table in tables:
            cols = {c['name']: c for c in inspector.get_columns(table)}
            assert 'id' in cols
            col_type = str(cols['id']['type']).upper()
            assert 'UUID' in col_type, f"{table}.id is not UUID (found: {col_type})"


class TestSecurityUtils:

    def test_hash_and_verify_password(self):
        from utils.security import hash_password, verify_password
        hashed = hash_password("TestPass123!")
        assert verify_password("TestPass123!", hashed) is True
        assert verify_password("WrongPass", hashed) is False

    def test_password_hash_is_different_each_time(self):
        from utils.security import hash_password
        assert hash_password("same") != hash_password("same")

    def test_make_otp_format(self):
        from utils.security import make_otp
        for _ in range(10):
            otp = make_otp()
            assert len(otp) == 6
            assert otp.isdigit()

    def test_make_access_token_payload(self):
        from utils.security import make_access_token, decode_token
        token = make_access_token("test-uuid", "ADMIN", None)
        payload = decode_token(token)
        assert payload["sub"] == "test-uuid"
        assert payload["role"] == "ADMIN"
        assert payload["class_id"] is None
        assert "exp" in payload

    def test_decode_invalid_token_raises(self):
        from utils.security import decode_token
        with pytest.raises(Exception):
            decode_token("this.is.not.valid")

    def test_hash_and_verify_refresh_token(self):
        from utils.security import hash_refresh_token, verify_refresh_token
        import uuid
        token = str(uuid.uuid4())
        hashed = hash_refresh_token(token)
        assert verify_refresh_token(token, hashed) is True
        assert verify_refresh_token("wrong", hashed) is False

    def test_make_mentor_reg_id_format(self):
        from utils.id_generator import make_mentor_reg_id
        for _ in range(5):
            reg_id = make_mentor_reg_id()
            assert reg_id.startswith("MENTOR-")
            assert len(reg_id) > 7


class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_health_returns_ok_status(self, client):
        assert client.get("/health").json()["status"] == "ok"

    def test_health_timestamp_ends_with_z(self, client):
        ts = client.get("/health").json()["timestamp"]
        assert ts.endswith("Z"), f"Timestamp must end with Z, got: {ts}"

    def test_health_no_auth_required(self, client):
        resp = client.get("/health")
        assert resp.status_code not in [401, 403]
