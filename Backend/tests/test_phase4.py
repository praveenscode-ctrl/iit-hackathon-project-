import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
import asyncio


class TestPhase4Base:
    @pytest.fixture(autouse=True)
    def setup_class_env(self, client, db, admin_headers):
        # Create a class, a mentor, and an active student
        c = client.post("/api/v1/classes", headers=admin_headers, json={"class_name": "P4 Class"}).json()
        self.class_id = c["id"]
        
        with patch("services.email_service.send_invite_email"):
            m = client.post("/api/v1/provision/manual/mentor", headers=admin_headers, json={
                "class_id": self.class_id, "full_name": "P4 Mentor", "email": "p4m@test.com", "password": "P4!", "is_primary_mentor": True
            }).json()
            s = client.post("/api/v1/provision/manual/student", headers=admin_headers, json={
                "class_id": self.class_id, "full_name": "P4 Student", "email": "p4s@test.com", "password": "P4!", "registration_id": "P4001"
            }).json()
        
        # Approve student
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{self.class_id}/students/{s['id']}/approve", headers=admin_headers, json={})
            
        # Logins
        self.m_token = client.post("/api/v1/auth/login", json={"email": "p4m@test.com", "password": "P4!", "registration_id": m["registration_id"], "fcm_token": ""}).json()["access_token"]
        self.s_token = client.post("/api/v1/auth/login", json={"email": "p4s@test.com", "password": "P4!", "registration_id": "P4001", "fcm_token": ""}).json()["access_token"]
        
        self.mentor_h = {"Authorization": f"Bearer {self.m_token}"}
        self.student_h = {"Authorization": f"Bearer {self.s_token}"}
        self.student_id = s["id"]


class TestAssignments(TestPhase4Base):
    
    def test_cp4_1_create_draft(self, client):
        resp = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": "A1", "content_type": "RICH_TEXT", "submission_type": "TEXT"
        })
        assert resp.status_code == 201
        assert resp.json()["status"] == "DRAFT"
        
    def test_cp4_2_student_cannot_see_draft(self, client):
        client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": "A2", "content_type": "RICH_TEXT", "submission_type": "TEXT"
        })
        resp = client.get(f"/api/v1/assignments?class_id={self.class_id}", headers=self.student_h)
        titles = [a["title"] for a in resp.json()["assignments"]]
        assert "A2" not in titles

    def test_cp4_3_publish_triggers_analytics(self, client, db):
        a_id = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": "A3", "content_type": "RICH_TEXT", "submission_type": "TEXT"
        }).json()["id"]
        
        with patch("services.fcm_service.send_batch_fcm") as mock_fcm:
            resp = client.post(f"/api/v1/assignments/{a_id}/publish", headers=self.mentor_h)
            assert resp.status_code == 200
            
        from models.analytics import AssignmentAnalytics
        import uuid
        row = db.query(AssignmentAnalytics).filter_by(assignment_id=uuid.UUID(a_id)).first()
        assert row.total_targets >= 1
        
    def test_cp4_4_student_can_see_published(self, client):
        a_id = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": "A4", "content_type": "RICH_TEXT", "submission_type": "TEXT"
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=self.mentor_h)
            
        resp = client.get(f"/api/v1/assignments?class_id={self.class_id}", headers=self.student_h)
        titles = [a["title"] for a in resp.json()["assignments"]]
        assert "A4" in titles

    def test_cp4_5_get_assignment_has_student_submission_for_student(self, client):
        a_id = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": "A5", "content_type": "RICH_TEXT", "submission_type": "TEXT"
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=self.mentor_h)
        
        resp = client.get(f"/api/v1/assignments/{a_id}", headers=self.student_h)
        data = resp.json()
        assert "student_submission" in data
        assert data["student_submission"]["submitted"] is False

    def test_cp4_6_get_assignment_has_student_submission_for_mentor(self, client):
        a_id = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": "A6", "content_type": "RICH_TEXT", "submission_type": "TEXT"
        }).json()["id"]
        resp = client.get(f"/api/v1/assignments/{a_id}", headers=self.mentor_h)
        data = resp.json()
        assert "student_submission" in data


class TestStorage(TestPhase4Base):
    
    def test_cp4_7_presigned_upload(self, client):
        with patch("boto3.client") as mock_boto:
            mock_s3 = mock_boto.return_value
            mock_s3.generate_presigned_url.return_value = "https://fake.upload.url"
            
            resp = client.post("/api/v1/storage/presigned-upload", headers=self.student_h, json={
                "file_name": "test.pdf", "file_type": "application/pdf", "upload_purpose": "SUBMISSION"
            })
            assert resp.status_code == 200
            assert "upload_url" in resp.json()
            assert "file_url" in resp.json()

    def test_cp4_20_presigned_download(self, client):
        with patch("boto3.client") as mock_boto:
            mock_s3 = mock_boto.return_value
            mock_s3.generate_presigned_url.return_value = "https://fake.download.url"
            
            resp = client.post("/api/v1/storage/presigned-download", headers=self.student_h, json={
                "file_url": "https://bucket.s3.region.amazonaws.com/submissions/key/test.pdf"
            })
            assert resp.status_code == 200
            assert "download_url" in resp.json()


class TestSubmissions(TestPhase4Base):
    
    @pytest.fixture
    def pub_assignment(self, client):
        a_id = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": "A_SUB", "content_type": "RICH_TEXT", "submission_type": "TEXT"
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=self.mentor_h)
        return a_id
        
    def test_cp4_8_submit_text(self, client, db, pub_assignment):
        with patch("websocket.tracker_ws.manager.broadcast"):
            resp = client.post(f"/api/v1/assignments/{pub_assignment}/submit", headers=self.student_h, json={
                "submission_type": "TEXT", "text_answer": "ans"
            })
        assert resp.status_code == 201
        assert resp.json()["version"] == 1
        
        from models.analytics import AssignmentAnalytics
        import uuid
        row = db.query(AssignmentAnalytics).filter_by(assignment_id=uuid.UUID(pub_assignment)).first()
        assert row.submitted_count == 1
        
    def test_cp4_9_resubmission_increments_version(self, client, pub_assignment):
        with patch("websocket.tracker_ws.manager.broadcast"):
            client.post(f"/api/v1/assignments/{pub_assignment}/submit", headers=self.student_h, json={
                "submission_type": "TEXT", "text_answer": "v1"
            })
            resp = client.post(f"/api/v1/assignments/{pub_assignment}/submit", headers=self.student_h, json={
                "submission_type": "TEXT", "text_answer": "v2"
            })
        assert resp.json()["version"] == 2
        
    def test_cp4_10_get_my_submissions(self, client, pub_assignment):
        with patch("websocket.tracker_ws.manager.broadcast"):
            client.post(f"/api/v1/assignments/{pub_assignment}/submit", headers=self.student_h, json={"submission_type": "TEXT", "text_answer": "v1"})
            client.post(f"/api/v1/assignments/{pub_assignment}/submit", headers=self.student_h, json={"submission_type": "TEXT", "text_answer": "v2"})
            
        resp = client.get("/api/v1/submissions/my", headers=self.student_h)
        subs = [s for s in resp.json()["submissions"] if s["assignment_id"] == pub_assignment]
        assert len(subs) == 1
        assert subs[0]["version"] == 2

    def test_cp4_11_tracker_status(self, client, pub_assignment):
        with patch("websocket.tracker_ws.manager.broadcast"):
            client.post(f"/api/v1/assignments/{pub_assignment}/submit", headers=self.student_h, json={"submission_type": "TEXT", "text_answer": "ans"})
            
        resp = client.get(f"/api/v1/assignments/{pub_assignment}/tracker", headers=self.mentor_h)
        assert resp.status_code == 200
        student = [s for s in resp.json()["students"] if s["student_id"] == self.student_id][0]
        assert student["tracker_status"] == "SUBMITTED"

    def test_cp4_12_get_submissions_mentor(self, client, pub_assignment):
        with patch("websocket.tracker_ws.manager.broadcast"):
            client.post(f"/api/v1/assignments/{pub_assignment}/submit", headers=self.student_h, json={"submission_type": "TEXT", "text_answer": "hello"})
            
        resp = client.get(f"/api/v1/assignments/{pub_assignment}/submissions", headers=self.mentor_h)
        subs = resp.json()["submissions"]
        assert len(subs) == 1
        assert subs[0]["text_answer"] == "hello"

    def test_cp4_13_manual_close_analytics(self, client, db, pub_assignment):
        with patch("websocket.tracker_ws.manager.broadcast"):
            client.post(f"/api/v1/assignments/{pub_assignment}/submit", headers=self.student_h, json={"submission_type": "TEXT", "text_answer": "ans"})
            client.post(f"/api/v1/assignments/{pub_assignment}/close", headers=self.mentor_h)
            
        from models.analytics import StudentAnalytics
        import uuid
        row = db.query(StudentAnalytics).filter_by(student_id=uuid.UUID(self.student_id)).first()
        assert row.completion_rate == 100.0


class TestJobsAndWebsockets(TestPhase4Base):

    def test_cp4_14_publish_deadline_jobs(self, client, db):
        future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        a_id = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": "A_JOB", "content_type": "RICH_TEXT", "submission_type": "TEXT", "deadline_at": future
        }).json()["id"]
        
        with patch("services.fcm_service.send_batch_fcm"), patch("scheduler.jobs.scheduler.add_job") as mock_add:
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=self.mentor_h)
        # Scheduler is mocked — 3 jobs should have been queued (close, remind_24h, remind_2h)
        assert mock_add.call_count == 3

    def test_cp4_19_student_reminder(self, client, db):
        a_id = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": "A_REM", "content_type": "RICH_TEXT", "submission_type": "TEXT"
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=self.mentor_h)
            
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        resp = client.post("/api/v1/notifications/reminder", headers=self.student_h, json={
            "assignment_id": a_id, "remind_at": future
        })
        assert resp.status_code == 201
        
        from models.notification import ReminderJob
        assert db.query(ReminderJob).count() >= 1
        
    def test_cp4_15_ws_connect(self, client, db):
        a_id = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": "A_WS", "content_type": "RICH_TEXT", "submission_type": "TEXT"
        }).json()["id"]
        
        # WebSocket handler uses SessionLocal() directly — patch it to return the test db
        with patch("websocket.tracker_ws.SessionLocal", return_value=db):
            with client.websocket_connect(f"/api/v1/ws/tracker/{a_id}?token={self.m_token}") as websocket:
                data = websocket.receive_json()
                assert data["event"] == "connected"

    def test_cp4_17_ws_fake_token(self, client):
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/api/v1/ws/tracker/1234?token=fake"):
                pass

    def test_cp4_18_ws_student_rejected(self, client):
        a_id = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": "A_WS2", "content_type": "RICH_TEXT", "submission_type": "TEXT"
        }).json()["id"]
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/api/v1/ws/tracker/{a_id}?token={self.s_token}"):
                pass
