import pytest
import io
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta
import time


# ---------------------------------------------------------------------------
# Shared base — provisions a class, mentor, two students, and creates/closes
# an assignment for dynamic analytics seeding
# ---------------------------------------------------------------------------

class TestPhase5Base:
    """Provisions a realistic class environment for all Phase-5 tests."""

    @pytest.fixture(autouse=True)
    def setup_env(self, client, db, admin_headers):
        # 1. Class
        c = client.post("/api/v1/classes", headers=admin_headers,
                        json={"class_name": "P5 Class"}).json()
        self.class_id = c["id"]

        # 2. Mentor + 2 students
        with patch("services.email_service.send_invite_email"):
            m = client.post("/api/v1/provision/manual/mentor", headers=admin_headers, json={
                "class_id": self.class_id, "full_name": "P5 Mentor",
                "email": "p5m@test.com", "password": "P5!", "is_primary_mentor": True
            }).json()
            s1 = client.post("/api/v1/provision/manual/student", headers=admin_headers, json={
                "class_id": self.class_id, "full_name": "Alice", "email": "alice@test.com",
                "password": "P5!", "registration_id": "P5A01"
            }).json()
            s2 = client.post("/api/v1/provision/manual/student", headers=admin_headers, json={
                "class_id": self.class_id, "full_name": "Bob", "email": "bob@test.com",
                "password": "P5!", "registration_id": "P5B02"
            }).json()

        # 3. Approve both students
        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{self.class_id}/students/{s1['id']}/approve",
                         headers=admin_headers, json={})
            client.patch(f"/api/v1/classes/{self.class_id}/students/{s2['id']}/approve",
                         headers=admin_headers, json={})

        # 4. Login all three
        self.mentor_token = client.post("/api/v1/auth/login", json={
            "email": "p5m@test.com", "password": "P5!",
            "registration_id": m["registration_id"], "fcm_token": ""
        }).json()["access_token"]

        self.alice_token = client.post("/api/v1/auth/login", json={
            "email": "alice@test.com", "password": "P5!",
            "registration_id": "P5A01", "fcm_token": ""
        }).json()["access_token"]

        self.bob_token = client.post("/api/v1/auth/login", json={
            "email": "bob@test.com", "password": "P5!",
            "registration_id": "P5B02", "fcm_token": ""
        }).json()["access_token"]

        self.mentor_h = {"Authorization": f"Bearer {self.mentor_token}"}
        self.alice_h = {"Authorization": f"Bearer {self.alice_token}"}
        self.bob_h = {"Authorization": f"Bearer {self.bob_token}"}
        self.alice_id = s1["id"]
        self.bob_id = s2["id"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _publish_assignment(self, client, title="A"):
        time.sleep(0.01)  # Guarantee strict created_at ordering in Postgres
        a_id = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": title,
            "content_type": "RICH_TEXT", "submission_type": "TEXT"
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=self.mentor_h)
        return a_id

    def _submit(self, client, a_id, token, answer="ans"):
        with patch("websocket.tracker_ws.manager.broadcast"):
            return client.post(f"/api/v1/assignments/{a_id}/submit",
                               headers={"Authorization": f"Bearer {token}"},
                               json={"submission_type": "TEXT", "text_answer": answer})

    def _close(self, client, a_id):
        with patch("websocket.tracker_ws.manager.broadcast"):
            return client.post(f"/api/v1/assignments/{a_id}/close", headers=self.mentor_h)


# ---------------------------------------------------------------------------
# Group A — Analytics API
# ---------------------------------------------------------------------------

class TestAnalyticsAPI(TestPhase5Base):

    # CP5-1
    def test_student_analytics_zeros_on_no_submissions(self, client, db):
        """No CLOSED assignments → all metrics are 0."""
        resp = client.get(f"/api/v1/analytics/students/{self.alice_id}",
                          headers=self.mentor_h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_assigned"] == 0
        assert data["total_submitted"] == 0
        assert data["completion_rate"] == 0.0
        assert data["risk_level"] == "NORMAL"

    # CP5-2
    def test_student_analytics_dynamic_after_close(self, client, db):
        """After submit + close → analytics reflect real numbers."""
        a_id = self._publish_assignment(client, "Analytics-A")
        self._submit(client, a_id, self.alice_token)
        self._close(client, a_id)

        db.expire_all()
        resp = client.get(f"/api/v1/analytics/students/{self.alice_id}",
                          headers=self.mentor_h)
        data = resp.json()
        assert data["total_assigned"] == 1
        assert data["total_submitted"] == 1
        assert data["completion_rate"] == 100.0

    # CP5-3
    def test_student_completion_rate_100(self, client, db):
        """Submit all closed assignments → 100.0 completion rate."""
        for i in range(3):
            a_id = self._publish_assignment(client, f"Full-{i}")
            self._submit(client, a_id, self.alice_token, f"answer {i}")
            self._close(client, a_id)

        db.expire_all()
        resp = client.get(f"/api/v1/analytics/students/{self.alice_id}",
                          headers=self.mentor_h)
        assert resp.json()["completion_rate"] == 100.0
        assert resp.json()["total_submitted"] == 3
        assert resp.json()["total_missed"] == 0

    # CP5-4
    def test_student_analytics_streaks(self, client, db):
        """Submit 3 in a row → current_streak == 3, longest_streak >= 3."""
        for i in range(3):
            a_id = self._publish_assignment(client, f"Streak-{i}")
            self._submit(client, a_id, self.alice_token)
            self._close(client, a_id)

        db.expire_all()
        resp = client.get(f"/api/v1/analytics/students/{self.alice_id}",
                          headers=self.mentor_h)
        data = resp.json()
        assert data["current_streak"] == 3
        assert data["longest_streak"] >= 3

    # CP5-5
    def test_student_risk_level_normal(self, client, db):
        """Student who submits everything is NORMAL risk."""
        a_id = self._publish_assignment(client, "Risk-Normal")
        self._submit(client, a_id, self.alice_token)
        self._close(client, a_id)

        db.expire_all()
        resp = client.get(f"/api/v1/analytics/students/{self.alice_id}",
                          headers=self.mentor_h)
        assert resp.json()["risk_level"] == "NORMAL"

    # CP5-6
    def test_class_analytics_endpoint_mentor(self, client, db):
        """Mentor can get class analytics overview."""
        resp = client.get(f"/api/v1/analytics/classes/{self.class_id}",
                          headers=self.mentor_h)
        assert resp.status_code == 200
        data = resp.json()
        assert "avg_completion" in data
        assert "total_students" in data
        assert "risk_distribution" in data

    # CP5-7
    def test_class_analytics_has_risk_distribution(self, client, db):
        """Risk distribution must have all 5 keys."""
        resp = client.get(f"/api/v1/analytics/classes/{self.class_id}",
                          headers=self.mentor_h)
        dist = resp.json()["risk_distribution"]
        for level in ["HIGH", "MEDIUM", "LOW", "NORMAL", "RECOVERING"]:
            assert level in dist

    # CP5-8
    def test_class_students_analytics_list(self, client, db):
        """Class students analytics list returns both Alice and Bob."""
        resp = client.get(f"/api/v1/analytics/classes/{self.class_id}/students",
                          headers=self.mentor_h)
        assert resp.status_code == 200
        students = resp.json()["students"]
        ids = [s["student_id"] for s in students]
        assert self.alice_id in ids
        assert self.bob_id in ids
        # Each row must have these fields from master architecture
        for s in students:
            assert "risk_level" in s
            assert "completion_rate" in s
            assert "total_submitted" in s
            assert "total_assigned" in s

    # CP5-9
    def test_admin_overview_counts(self, client, db, admin_headers):
        """Admin overview correctly reflects at least 1 class, 1 mentor, 2 students."""
        resp = client.get("/api/v1/analytics/admin/overview", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_classes"] >= 1
        assert data["total_mentors"] >= 1
        assert data["total_students"] >= 2
        assert "classes" in data
        assert len(data["classes"]) >= 1
        # Each class card must have required fields
        card = data["classes"][0]
        for field in ["class_id", "class_name", "avg_completion", "high_risk_count", "student_count"]:
            assert field in card

    # CP5-10
    def test_student_cannot_access_other_student_analytics(self, client):
        """Alice cannot view Bob's analytics — must get 403."""
        resp = client.get(f"/api/v1/analytics/students/{self.bob_id}",
                          headers=self.alice_h)
        assert resp.status_code == 403

    # CP5-11
    def test_risk_students_list_only_at_risk(self, client, db):
        """Risk list only includes HIGH/MEDIUM students, not those with NORMAL risk."""
        # Alice submits all — she is NORMAL
        a_id = self._publish_assignment(client, "Risk-List")
        self._submit(client, a_id, self.alice_token)
        self._close(client, a_id)

        resp = client.get(f"/api/v1/analytics/risk/students?class_id={self.class_id}",
                          headers=self.mentor_h)
        assert resp.status_code == 200
        # Response key is 'at_risk_students' per architecture §1335
        student_ids = [s["student_id"] for s in resp.json()["at_risk_students"]]
        # Alice should NOT be in risk list (she submitted)
        assert self.alice_id not in student_ids
        # Each returned student must be HIGH/MEDIUM/LOW/RECOVERING
        for s in resp.json()["at_risk_students"]:
            assert s["risk_level"] in ["HIGH", "MEDIUM", "LOW", "RECOVERING"]

    # CP5-12
    def test_class_analytics_has_bottleneck_assignments(self, client, db):
        """An assignment where Bob submits but Alice doesn't (<100% but not bottleneck at 50% with 1/2).
        Create scenario where NEITHER submits (0% → is_bottleneck=True)."""
        a_id = self._publish_assignment(client, "Bottleneck")
        # Nobody submits → 0% completion
        self._close(client, a_id)

        db.expire_all()
        resp = client.get(f"/api/v1/analytics/classes/{self.class_id}",
                          headers=self.mentor_h)
        bottlenecks = resp.json().get("bottleneck_assignments", [])
        bottleneck_ids = [b["assignment_id"] for b in bottlenecks]
        assert a_id in bottleneck_ids


# ---------------------------------------------------------------------------
# Group B — Risk Engine Logic (code-level + API integration)
# ---------------------------------------------------------------------------

class TestRiskEngine(TestPhase5Base):

    # CP5-13
    def test_risk_high_after_3_consecutive_misses(self, client, db):
        """3 consecutive CLOSED assignments with zero submissions → HIGH risk."""
        for i in range(3):
            a_id = self._publish_assignment(client, f"Miss-{i}")
            # Alice DOES NOT submit — Bob doesn't either
            self._close(client, a_id)

        db.expire_all()
        resp = client.get(f"/api/v1/analytics/students/{self.alice_id}",
                          headers=self.mentor_h)
        assert resp.json()["risk_level"] == "HIGH"
        assert resp.json()["consecutive_misses"] == 3

    # CP5-14
    def test_risk_medium_below_40_percent(self, client, db):
        """Submit 1 out of 3 → 33% completion → MEDIUM risk."""
        # Assignment 1 — Alice submits
        a1 = self._publish_assignment(client, "MedA1")
        self._submit(client, a1, self.alice_token)
        self._close(client, a1)

        # Assignments 2 & 3 — Alice does NOT submit
        for i in range(2):
            a = self._publish_assignment(client, f"MedA{2+i}")
            self._close(client, a)

        db.expire_all()
        resp = client.get(f"/api/v1/analytics/students/{self.alice_id}",
                          headers=self.mentor_h)
        data = resp.json()
        assert data["completion_rate"] < 40.0
        assert data["risk_level"] in ["MEDIUM", "HIGH"]

    # CP5-15
    def test_risk_recovering_after_high(self, client, db):
        """Goes HIGH (3 consecutive misses while still at 70%), then submits 1 more → RECOVERING."""
        # Submit 7 first → all submitted, 100% → NORMAL
        for i in range(7):
            a_id = self._publish_assignment(client, f"Rec-Sub-{i}")
            self._submit(client, a_id, self.alice_token)
            self._close(client, a_id)

        # 3 consecutive misses → consecutive_misses=3, completion=7/10=70% → HIGH
        for i in range(3):
            a_id = self._publish_assignment(client, f"Rec-Miss-{i}")
            self._close(client, a_id)  # Alice does NOT submit

        # Verify HIGH first
        db.expire_all()
        mid_resp = client.get(f"/api/v1/analytics/students/{self.alice_id}",
                              headers=self.mentor_h).json()
        assert mid_resp["risk_level"] == "HIGH"

        # Now 1 more submission → consecutive_misses=0, completion=8/11=72.7% ≥60%, prev=HIGH → RECOVERING
        a_id = self._publish_assignment(client, "Rec-Comeback")
        self._submit(client, a_id, self.alice_token)
        self._close(client, a_id)

        db.expire_all()
        resp = client.get(f"/api/v1/analytics/students/{self.alice_id}",
                          headers=self.mentor_h)
        data = resp.json()
        # 8/11 = 72.7% — consecutive_misses=0 — prev was HIGH → RECOVERING
        assert data["risk_level"] == "RECOVERING"
        assert data["completion_rate"] >= 60.0

    # CP5-16
    def test_recompute_all_after_close_updates_all_students(self, client, db):
        """Closing one assignment recomputes analytics for ALL students in class."""
        a_id = self._publish_assignment(client, "Recompute-All")
        self._submit(client, a_id, self.alice_token)
        # Bob does NOT submit
        self._close(client, a_id)

        db.expire_all()
        alice_resp = client.get(f"/api/v1/analytics/students/{self.alice_id}",
                                headers=self.mentor_h).json()
        bob_resp = client.get(f"/api/v1/analytics/students/{self.bob_id}",
                              headers=self.mentor_h).json()

        # Alice submitted → 1 assigned, 1 submitted
        assert alice_resp["total_submitted"] == 1
        assert alice_resp["total_assigned"] == 1
        # Bob did not submit → 1 assigned, 0 submitted, 1 missed
        assert bob_resp["total_submitted"] == 0
        assert bob_resp["total_assigned"] == 1
        assert bob_resp["total_missed"] == 1


# ---------------------------------------------------------------------------
# Group C — Export API
# ---------------------------------------------------------------------------

class TestExportAPI(TestPhase5Base):

    # CP5-18
    def test_export_rejected_if_not_closed(self, client, db):
        a_id = self._publish_assignment(client, "Export-Pub")
        resp = client.post("/api/v1/exports/assignment-tracker",
                           headers=self.mentor_h,
                           json={"assignment_id": a_id})
        assert resp.status_code == 409

    # CP5-19
    def test_export_starts_and_completes(self, client, db):
        a_id = self._publish_assignment(client, "Export-Close")
        self._close(client, a_id)

        # Mock S3 upload
        with patch("services.export_service.s3.upload_file"):
            resp = client.post("/api/v1/exports/assignment-tracker",
                               headers=self.mentor_h,
                               json={"assignment_id": a_id})
            assert resp.status_code == 202
            job_id = resp.json()["export_job_id"]

            # Because background tasks run in the same process synchronously in TestClient,
            # it should be DONE immediately upon next query.
            poll = client.get(f"/api/v1/exports/{job_id}", headers=self.mentor_h)
            assert poll.status_code == 200
            assert poll.json()["status"] == "DONE"
            assert "file_url" in poll.json()

    # CP5-21
    def test_student_cannot_export(self, client):
        resp = client.post("/api/v1/exports/assignment-tracker",
                           headers=self.alice_h,
                           json={"assignment_id": "some-id"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Group D — AI Query (all 6 intents + safety + logging)
# ---------------------------------------------------------------------------

def make_mock_llm(intent: str, params: dict):
    """Returns an async mock that simulates LLM returning a specific intent."""
    import json
    async def _mock(*args, **kwargs):
        return json.dumps({"intent": intent, "params": params})
    return _mock


class TestAIQuery(TestPhase5Base):

    # CP5-20
    def test_ai_who_missed_assignment(self, client, db):
        """AI: 'who_missed_assignment' returns list of students who didn't submit."""
        a_id = self._publish_assignment(client, "Assignment 1")
        # Only Alice submits — Bob misses
        self._submit(client, a_id, self.alice_token)
        self._close(client, a_id)

        with patch("services.ai_service.call_llm_api",
                   side_effect=make_mock_llm("who_missed_assignment",
                                             {"assignment_ref": "Assignment 1"})):
            resp = client.post("/api/v1/ai/query", headers=self.mentor_h, json={
                "class_id": self.class_id,
                "query_text": "Who hasn't submitted Assignment 1?"
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "who_missed_assignment"
        assert data["result"]["type"] == "student_list"
        names = [s["full_name"] for s in data["result"]["data"]]
        assert "Bob" in names
        assert "Alice" not in names

    # CP5-21
    def test_ai_student_completion_rate(self, client, db):
        """AI: 'student_completion_rate' returns Alice's real completion rate."""
        a_id = self._publish_assignment(client, "Rate-Test")
        self._submit(client, a_id, self.alice_token)
        self._close(client, a_id)

        with patch("services.ai_service.call_llm_api",
                   side_effect=make_mock_llm("student_completion_rate",
                                             {"student_name": "Alice"})):
            resp = client.post("/api/v1/ai/query", headers=self.mentor_h, json={
                "class_id": self.class_id,
                "query_text": "What is Alice's completion rate?"
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "student_completion_rate"
        assert data["result"]["type"] == "student_profile"
        student_data = data["result"]["data"][0]
        assert student_data["full_name"] == "Alice"
        assert student_data["completion_rate"] == 100.0

    # CP5-22
    def test_ai_class_summary(self, client, db):
        """AI: 'class_summary' returns aggregated class analytics."""
        a_id = self._publish_assignment(client, "Summary-Test")
        self._submit(client, a_id, self.alice_token)
        self._close(client, a_id)

        with patch("services.ai_service.call_llm_api",
                   side_effect=make_mock_llm("class_summary", {})):
            resp = client.post("/api/v1/ai/query", headers=self.mentor_h, json={
                "class_id": self.class_id,
                "query_text": "How is the class doing?"
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["type"] == "class_summary"
        summary = data["result"]["data"][0]
        assert "avg_completion" in summary
        assert "total_students" in summary
        assert "avg_late_rate" in summary

    # CP5-23
    def test_ai_risk_students(self, client, db):
        """AI: 'risk_students' returns students at HIGH/MEDIUM risk."""
        # 3 closes with no submissions → Bob and Alice both get HIGH
        for i in range(3):
            a = self._publish_assignment(client, f"Risk-AI-{i}")
            self._close(client, a)

        with patch("services.ai_service.call_llm_api",
                   side_effect=make_mock_llm("risk_students", {})):
            resp = client.post("/api/v1/ai/query", headers=self.mentor_h, json={
                "class_id": self.class_id,
                "query_text": "Show me students in danger"
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["type"] == "risk_list"
        risk_levels = [s["risk_level"] for s in data["result"]["data"]]
        for level in risk_levels:
            assert level in ["HIGH", "MEDIUM"]

    # CP5-24
    def test_ai_student_not_found(self, client, db):
        """AI: asking for an unknown student name returns no_data gracefully."""
        with patch("services.ai_service.call_llm_api",
                   side_effect=make_mock_llm("student_completion_rate",
                                             {"student_name": "NonExistentXYZ"})):
            resp = client.post("/api/v1/ai/query", headers=self.mentor_h, json={
                "class_id": self.class_id,
                "query_text": "What is NonExistentXYZ's completion rate?"
            })

        assert resp.status_code == 200
        assert resp.json()["result"]["type"] == "no_data"

    # CP5-25
    def test_ai_unknown_intent(self, client, db):
        """AI: completely off-topic queries return no_data, not crash."""
        with patch("services.ai_service.call_llm_api",
                   side_effect=make_mock_llm("unknown", {})):
            resp = client.post("/api/v1/ai/query", headers=self.mentor_h, json={
                "class_id": self.class_id,
                "query_text": "What is the weather in Chennai today?"
            })

        assert resp.status_code == 200
        assert resp.json()["result"]["type"] == "no_data"
        assert resp.json()["intent"] == "unknown"

    # CP5-26
    def test_ai_student_cannot_query(self, client):
        """Student role must be rejected from AI endpoint with 403."""
        resp = client.post("/api/v1/ai/query", headers=self.alice_h, json={
            "class_id": self.class_id,
            "query_text": "Who missed the last assignment?"
        })
        assert resp.status_code == 403

    # CP5-27
    def test_ai_response_logs_to_db(self, client, db):
        """Every AI query call must save an entry to ai_query_logs."""
        from models.export import AiQueryLog

        initial_count = db.query(AiQueryLog).count()

        with patch("services.ai_service.call_llm_api",
                   side_effect=make_mock_llm("class_summary", {})):
            client.post("/api/v1/ai/query", headers=self.mentor_h, json={
                "class_id": self.class_id,
                "query_text": "Give me a class summary"
            })

        db.expire_all()
        final_count = db.query(AiQueryLog).count()
        assert final_count == initial_count + 1
