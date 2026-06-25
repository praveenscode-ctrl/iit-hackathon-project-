import pytest
from unittest.mock import patch


class TestAdminSignup:

    def test_signup_returns_201(self, client):
        with patch("services.email_service.send_otp_email"):
            resp = client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Admin", "email": "new@test.com", "password": "Test1234!"
            })
        assert resp.status_code == 201

    def test_signup_creates_pending_user(self, client, db):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={
                "full_name": "Pend", "email": "pend@test.com", "password": "Test1234!"
            })
        from models.user import User
        u = db.query(User).filter_by(email="pend@test.com").first()
        assert u.role == "ADMIN"
        assert u.status == "PENDING_OTP"

    def test_duplicate_email_returns_409(self, client):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={"full_name": "A", "email": "dup@test.com", "password": "Test1234!"})
            resp = client.post("/api/v1/auth/admin/signup", json={"full_name": "B", "email": "dup@test.com", "password": "Test1234!"})
        assert resp.status_code == 409


class TestOtpVerify:

    def _make(self, client, db, email):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={"full_name": "T", "email": email, "password": "Test1234!"})
        from models.user import OtpVerification
        return db.query(OtpVerification).filter_by(email=email).first().otp_code

    def test_correct_otp_returns_tokens(self, client, db):
        otp = self._make(client, db, "ok@test.com")
        resp = client.post("/api/v1/auth/admin/verify-otp", json={"email": "ok@test.com", "otp": otp})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_correct_otp_activates_user(self, client, db):
        otp = self._make(client, db, "act@test.com")
        client.post("/api/v1/auth/admin/verify-otp", json={"email": "act@test.com", "otp": otp})
        from models.user import User
        assert db.query(User).filter_by(email="act@test.com").first().status == "ACTIVE"

    def test_correct_otp_creates_admin_profile(self, client, db):
        otp = self._make(client, db, "prof@test.com")
        client.post("/api/v1/auth/admin/verify-otp", json={"email": "prof@test.com", "otp": otp})
        from models.user import User, AdminProfile
        u = db.query(User).filter_by(email="prof@test.com").first()
        assert db.query(AdminProfile).filter_by(user_id=u.id).first() is not None

    def test_wrong_otp_returns_400(self, client, db):
        self._make(client, db, "wrong@test.com")
        resp = client.post("/api/v1/auth/admin/verify-otp", json={"email": "wrong@test.com", "otp": "000000"})
        assert resp.status_code == 400

    def test_expired_otp_returns_410(self, client, db):
        self._make(client, db, "exp@test.com")
        from sqlalchemy import text
        db.execute(text("UPDATE otp_verifications SET expires_at = now() - interval '1 minute' WHERE email='exp@test.com'"))
        db.commit()
        resp = client.post("/api/v1/auth/admin/verify-otp", json={"email": "exp@test.com", "otp": "123456"})
        assert resp.status_code == 410


class TestLogin:

    def _verified(self, client, db, email):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={"full_name": "L", "email": email, "password": "Test1234!"})
        from models.user import OtpVerification
        otp = db.query(OtpVerification).filter_by(email=email).first().otp_code
        client.post("/api/v1/auth/admin/verify-otp", json={"email": email, "otp": otp})

    def test_admin_login_returns_200(self, client, db):
        self._verified(client, db, "al@test.com")
        resp = client.post("/api/v1/auth/login", json={"email": "al@test.com", "password": "Test1234!", "registration_id": "", "fcm_token": ""})
        assert resp.status_code == 200

    def test_admin_login_has_all_user_fields(self, client, db):
        self._verified(client, db, "af@test.com")
        resp = client.post("/api/v1/auth/login", json={"email": "af@test.com", "password": "Test1234!", "registration_id": "", "fcm_token": ""})
        for f in ["id", "full_name", "email", "role", "class_id", "class_name", "registration_id"]:
            assert f in resp.json()["user"], f"MISSING: user.{f}"

    def test_admin_class_id_is_null(self, client, db):
        self._verified(client, db, "null@test.com")
        resp = client.post("/api/v1/auth/login", json={"email": "null@test.com", "password": "Test1234!", "registration_id": "", "fcm_token": ""})
        assert resp.json()["user"]["class_id"] is None

    def test_wrong_password_returns_401(self, client, db):
        self._verified(client, db, "bad@test.com")
        resp = client.post("/api/v1/auth/login", json={"email": "bad@test.com", "password": "Wrong!", "registration_id": "", "fcm_token": ""})
        assert resp.status_code == 401

    def test_unknown_email_returns_401(self, client, db):
        resp = client.post("/api/v1/auth/login", json={"email": "nobody@x.com", "password": "P", "registration_id": "", "fcm_token": ""})
        assert resp.status_code == 401


class TestTokenRefresh:

    def _tokens(self, client, db, email):
        with patch("services.email_service.send_otp_email"):
            client.post("/api/v1/auth/admin/signup", json={"full_name": "R", "email": email, "password": "Test1234!"})
        from models.user import OtpVerification
        otp = db.query(OtpVerification).filter_by(email=email).first().otp_code
        resp = client.post("/api/v1/auth/admin/verify-otp", json={"email": email, "otp": otp})
        return resp.json()["access_token"], resp.json()["refresh_token"]

    def test_refresh_returns_new_token(self, client, db):
        _, refresh = self._tokens(client, db, "ref@test.com")
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_invalid_refresh_returns_401(self, client, db):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "bad"})
        assert resp.status_code == 401

    def test_revoked_refresh_returns_401(self, client, db):
        access, refresh = self._tokens(client, db, "rev@test.com")
        client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access}"}, json={"refresh_token": refresh})
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 401


class TestGetMe:

    def test_me_returns_all_fields(self, client, admin_headers):
        resp = client.get("/api/v1/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        for f in ["id", "full_name", "email", "role", "registration_id", "class_id", "class_name", "status"]:
            assert f in resp.json()

    def test_me_without_token_returns_4xx(self, client):
        assert client.get("/api/v1/auth/me").status_code in [401, 422]

    def test_me_with_fake_token_returns_401(self, client):
        assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake.token"}).status_code == 401

    def test_me_returns_correct_role(self, client, admin_headers):
        assert client.get("/api/v1/auth/me", headers=admin_headers).json()["role"] == "ADMIN"
