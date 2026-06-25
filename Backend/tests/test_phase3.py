import pytest
from unittest.mock import patch


class TestClassCreation:

    def test_create_class_returns_201(self, client, admin_headers):
        resp = client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "Test Class"})
        assert resp.status_code == 201

    def test_create_class_response_shape(self, client, admin_headers):
        resp = client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "Shape Class"})
        data = resp.json()
        for f in ["id", "class_name", "status", "created_at"]:
            assert f in data
        assert data["status"] == "ACTIVE"

    def test_create_class_creates_analytics_row(self, client, db, admin_headers):
        resp = client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "Analytics Class"})
        class_id = resp.json()["id"]
        from models.analytics import ClassAnalytics
        import uuid
        row = db.query(ClassAnalytics).filter_by(class_id=uuid.UUID(class_id)).first()
        assert row is not None
        assert row.total_students == 0

    def test_mentor_cannot_create_class(self, client, admin_headers):
        with patch("services.email_service.send_invite_email"):
            c = client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "MC"}).json()["id"]
            m = client.post("/api/v1/provision/manual/mentor", headers=admin_headers, json={
                "class_id": c, "full_name": "M", "email": "mtc@test.com", "password": "Mentor1234!", "is_primary_mentor": True
            })
        reg = m.json()["registration_id"]
        t = client.post("/api/v1/auth/login", json={"email": "mtc@test.com", "password": "Mentor1234!", "registration_id": reg, "fcm_token": ""}).json()["access_token"]
        resp = client.post("/api/v1/classes", headers={"Authorization": f"Bearer {t}"}, json={"class_name": "Hack"})
        assert resp.status_code == 403

    def test_get_classes_returns_list(self, client, admin_headers):
        client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "C1"})
        resp = client.get("/api/v1/classes", headers=admin_headers)
        assert resp.status_code == 200
        assert "classes" in resp.json()

    def test_get_classes_includes_counts(self, client, admin_headers):
        client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "CC"})
        classes = client.get("/api/v1/classes", headers=admin_headers).json()["classes"]
        for c in classes:
            assert "student_count" in c
            assert "mentor_count" in c


class TestProvisioning:

    def _cls(self, client, admin_headers):
        return client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "P Class"}).json()["id"]

    def test_provision_mentor_returns_mentor_reg_id(self, client, admin_headers):
        cid = self._cls(client, admin_headers)
        with patch("services.email_service.send_invite_email"):
            resp = client.post("/api/v1/provision/manual/mentor", headers=admin_headers, json={
                "class_id": cid, "full_name": "M", "email": "pm@test.com", "password": "M1234!", "is_primary_mentor": True
            })
        assert resp.status_code == 201
        assert resp.json()["registration_id"].startswith("MENTOR-")

    def test_provision_mentor_creates_active_membership(self, client, db, admin_headers):
        cid = self._cls(client, admin_headers)
        with patch("services.email_service.send_invite_email"):
            resp = client.post("/api/v1/provision/manual/mentor", headers=admin_headers, json={
                "class_id": cid, "full_name": "AM", "email": "am@test.com", "password": "M1234!", "is_primary_mentor": False
            })
        import uuid
        from models.class_ import ClassMembership
        m = db.query(ClassMembership).filter_by(user_id=uuid.UUID(resp.json()["id"])).first()
        assert m.status == "ACTIVE"

    def test_provision_student_creates_pending_membership(self, client, db, admin_headers):
        cid = self._cls(client, admin_headers)
        with patch("services.email_service.send_invite_email"):
            resp = client.post("/api/v1/provision/manual/student", headers=admin_headers, json={
                "class_id": cid, "full_name": "S", "email": "ps@test.com", "password": "S1234!", "registration_id": "R001"
            })
        assert resp.status_code == 201
        import uuid
        from models.class_ import ClassMembership
        m = db.query(ClassMembership).filter_by(user_id=uuid.UUID(resp.json()["id"])).first()
        assert m.status == "PENDING", f"Must be PENDING, got {m.status}"

    def test_duplicate_email_returns_409(self, client, admin_headers):
        cid = self._cls(client, admin_headers)
        with patch("services.email_service.send_invite_email"):
            client.post("/api/v1/provision/manual/mentor", headers=admin_headers, json={
                "class_id": cid, "full_name": "M1", "email": "dup_m@test.com", "password": "P", "is_primary_mentor": False
            })
            resp = client.post("/api/v1/provision/manual/mentor", headers=admin_headers, json={
                "class_id": cid, "full_name": "M2", "email": "dup_m@test.com", "password": "P", "is_primary_mentor": False
            })
        assert resp.status_code == 409


class TestApprovalFlow:

    def _setup(self, client, db, admin_headers):
        cid = client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "App Class"}).json()["id"]
        with patch("services.email_service.send_invite_email"):
            mr = client.post("/api/v1/provision/manual/mentor", headers=admin_headers, json={
                "class_id": cid, "full_name": "App M", "email": "appm@test.com", "password": "M1234!", "is_primary_mentor": True
            })
            sr = client.post("/api/v1/provision/manual/student", headers=admin_headers, json={
                "class_id": cid, "full_name": "App S", "email": "apps@test.com", "password": "S1234!", "registration_id": "AP001"
            })
        reg = mr.json()["registration_id"]
        t = client.post("/api/v1/auth/login", json={"email": "appm@test.com", "password": "M1234!", "registration_id": reg, "fcm_token": ""}).json()["access_token"]
        return cid, sr.json()["id"], {"Authorization": f"Bearer {t}"}

    def test_pending_student_blocked(self, client, db, admin_headers):
        self._setup(client, db, admin_headers)
        resp = client.post("/api/v1/auth/login", json={"email": "apps@test.com", "password": "S1234!", "registration_id": "AP001", "fcm_token": ""})
        assert resp.status_code == 403

    def test_approvals_list_returns_pending(self, client, db, admin_headers):
        cid, _, mh = self._setup(client, db, admin_headers)
        resp = client.get(f"/api/v1/classes/{cid}/approvals", headers=mh)
        assert resp.json()["pending_count"] == 1
        for f in ["student_id", "full_name", "email", "registration_id", "requested_at", "joined_via"]:
            assert f in resp.json()["pending"][0]

    def test_approve_changes_status_to_active(self, client, db, admin_headers):
        cid, sid, mh = self._setup(client, db, admin_headers)
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{cid}/students/{sid}/approve", headers=mh, json={})
        from models.class_ import ClassMembership
        import uuid
        m = db.query(ClassMembership).filter_by(user_id=uuid.UUID(sid), class_id=uuid.UUID(cid)).first()
        assert m.status == "ACTIVE"

    def test_approve_creates_student_analytics_row(self, client, db, admin_headers):
        cid, sid, mh = self._setup(client, db, admin_headers)
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{cid}/students/{sid}/approve", headers=mh, json={})
        from models.analytics import StudentAnalytics
        import uuid
        row = db.query(StudentAnalytics).filter_by(student_id=uuid.UUID(sid), class_id=uuid.UUID(cid)).first()
        assert row is not None
        assert row.risk_level == "NORMAL"

    def test_approve_creates_notification(self, client, db, admin_headers):
        cid, sid, mh = self._setup(client, db, admin_headers)
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{cid}/students/{sid}/approve", headers=mh, json={})
        from models.notification import Notification
        import uuid
        n = db.query(Notification).filter_by(user_id=uuid.UUID(sid), notification_type="STUDENT_APPROVED").first()
        assert n is not None

    def test_student_can_login_after_approval(self, client, db, admin_headers):
        cid, sid, mh = self._setup(client, db, admin_headers)
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{cid}/students/{sid}/approve", headers=mh, json={})
        resp = client.post("/api/v1/auth/login", json={"email": "apps@test.com", "password": "S1234!", "registration_id": "AP001", "fcm_token": ""})
        assert resp.status_code == 200
        assert resp.json()["user"]["class_id"] == cid

    def test_reject_changes_status(self, client, db, admin_headers):
        cid, sid, mh = self._setup(client, db, admin_headers)
        with patch("services.fcm_service.send_single_fcm"):
            resp = client.patch(f"/api/v1/classes/{cid}/students/{sid}/reject", headers=mh, json={"reason": "Test"})
        assert resp.status_code == 200
        from models.class_ import ClassMembership
        import uuid
        m = db.query(ClassMembership).filter_by(user_id=uuid.UUID(sid)).first()
        assert m.status == "REJECTED"
        assert m.rejection_reason == "Test"

    def test_students_list_uses_membership_status_field(self, client, db, admin_headers):
        cid, sid, mh = self._setup(client, db, admin_headers)
        resp = client.get(f"/api/v1/classes/{cid}/students", headers=mh)
        assert resp.status_code == 200
        students = resp.json()["students"]
        if students:
            assert "membership_status" in students[0], "Field must be 'membership_status' not 'status'"
            assert "status" not in students[0], "Must not have raw 'status' field in students list"


class TestBulkImport:

    def test_template_downloads(self, client, admin_headers):
        resp = client.get("/api/v1/provision/bulk-import/template", headers=admin_headers)
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        assert "openxmlformats" in ct or "spreadsheet" in ct

    def test_template_has_three_sheets(self, client, admin_headers):
        import io, openpyxl
        resp = client.get("/api/v1/provision/bulk-import/template", headers=admin_headers)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        assert "Classes" in wb.sheetnames
        assert "Mentors" in wb.sheetnames
        assert "Students" in wb.sheetnames

    def test_bulk_import_returns_202(self, client, admin_headers):
        import io, openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Classes"
        ws.append(["Class Name", "Description", "Academic Year"])
        wb.create_sheet("Mentors").append(["Class Name", "Full Name", "Email", "Password", "Is Primary"])
        wb.create_sheet("Students").append(["Class Name", "Full Name", "Email", "Password", "Registration ID"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        with patch("services.email_service.send_invite_email"):
            resp = client.post("/api/v1/provision/bulk-import", headers=admin_headers,
                               files={"file": ("import.xlsx", buf.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert resp.status_code == 202
        assert "batch_id" in resp.json()
