"""Diagnostic test to trace the RECOVERING risk flow step by step."""
import pytest
from unittest.mock import patch
import time


class TestRecoveringDebug:
    @pytest.fixture(autouse=True)
    def setup_env(self, client, db, admin_headers):
        c = client.post("/api/v1/classes", headers=admin_headers,
                        json={"class_name": "Debug Class"}).json()
        self.class_id = c["id"]

        with patch("services.email_service.send_invite_email"):
            m = client.post("/api/v1/provision/manual/mentor", headers=admin_headers, json={
                "class_id": self.class_id, "full_name": "Debug Mentor",
                "email": "dbgm@test.com", "password": "P5!", "is_primary_mentor": True
            }).json()
            s1 = client.post("/api/v1/provision/manual/student", headers=admin_headers, json={
                "class_id": self.class_id, "full_name": "DebugAlice", "email": "dbga@test.com",
                "password": "P5!", "registration_id": "DBG01"
            }).json()

        with patch("services.fcm_service.send_single_fcm"):
            client.patch(f"/api/v1/classes/{self.class_id}/students/{s1['id']}/approve",
                         headers=admin_headers, json={})

        self.mentor_token = client.post("/api/v1/auth/login", json={
            "email": "dbgm@test.com", "password": "P5!",
            "registration_id": m["registration_id"], "fcm_token": ""
        }).json()["access_token"]
        self.alice_token = client.post("/api/v1/auth/login", json={
            "email": "dbga@test.com", "password": "P5!",
            "registration_id": "DBG01", "fcm_token": ""
        }).json()["access_token"]

        self.mentor_h = {"Authorization": f"Bearer {self.mentor_token}"}
        self.alice_h = {"Authorization": f"Bearer {self.alice_token}"}
        self.alice_id = s1["id"]

    def _pub(self, client, title):
        time.sleep(0.05)
        a_id = client.post("/api/v1/assignments", headers=self.mentor_h, json={
            "class_id": self.class_id, "title": title,
            "content_type": "RICH_TEXT", "submission_type": "TEXT"
        }).json()["id"]
        with patch("services.fcm_service.send_batch_fcm"):
            client.post(f"/api/v1/assignments/{a_id}/publish", headers=self.mentor_h)
        return a_id

    def _sub(self, client, a_id):
        with patch("websocket.tracker_ws.manager.broadcast"):
            client.post(f"/api/v1/assignments/{a_id}/submit",
                        headers=self.alice_h,
                        json={"submission_type": "TEXT", "text_answer": "ans"})

    def _close(self, client, a_id):
        with patch("websocket.tracker_ws.manager.broadcast"):
            client.post(f"/api/v1/assignments/{a_id}/close", headers=self.mentor_h)

    def _get_analytics(self, client, db):
        db.expire_all()
        return client.get(f"/api/v1/analytics/students/{self.alice_id}",
                          headers=self.mentor_h).json()

    def test_trace_recovering(self, client, db):
        # Step 1: submit 3, close 3
        for i in range(3):
            a = self._pub(client, f"Sub-{i}")
            self._sub(client, a)
            self._close(client, a)

        state = self._get_analytics(client, db)
        print(f"\n[After 3 submitted] risk={state['risk_level']} comp={state['completion_rate']} "
              f"consec_miss={state['consecutive_misses']} streak={state['current_streak']}")
        assert state["risk_level"] == "NORMAL"

        # Step 2: miss 3 in a row
        for i in range(3):
            a = self._pub(client, f"Miss-{i}")
            self._close(client, a)
            s = self._get_analytics(client, db)
            print(f"[After miss #{i+1}] risk={s['risk_level']} comp={s['completion_rate']} "
                  f"consec_miss={s['consecutive_misses']}")

        state = self._get_analytics(client, db)
        print(f"\n[After 3 misses total] risk={state['risk_level']} comp={state['completion_rate']} "
              f"consec_miss={state['consecutive_misses']}")
        assert state["risk_level"] == "HIGH", f"Expected HIGH but got {state['risk_level']}"
