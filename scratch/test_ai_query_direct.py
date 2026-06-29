import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Backend")))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from unittest.mock import patch

client = TestClient(app)
db = SessionLocal()

# Let's find a class, mentor, and student to test with
from models.user import User
from models.class_ import Class, ClassMembership
from models.analytics import StudentAnalytics

admin = db.query(User).filter_by(role="ADMIN").first()
if not admin:
    print("No admin user found")
    sys.exit(1)

# Let's get class
c = db.query(Class).first()
if not c:
    print("No class found")
    sys.exit(1)

mentor = db.query(User).join(ClassMembership).filter(ClassMembership.class_id == c.id, User.role == "MENTOR").first()
if not mentor:
    print("No mentor found")
    sys.exit(1)

# Login mentor to get token
resp = client.post("/api/v1/auth/login", json={
    "email": mentor.email,
    "password": "Password123", # standard password or whatever standard is
    "registration_id": mentor.registration_id,
    "fcm_token": ""
})
if resp.status_code != 200:
    print("Login failed:", resp.json())
    # Try alternate password or get token directly
    # Since we are in python, we can forge or bypass auth if we want, but let's see.

# Wait, let's just mock call_llm_api and call process_ai_query directly!
from services.ai_service import process_ai_query

async def test_direct():
    import json
    async def mock_llm(*args, **kwargs):
        return json.dumps({"intent": "risk_students", "params": {}})
        
    with patch("services.ai_service.call_llm_api", side_effect=mock_llm):
        res = await process_ai_query(str(c.id), "Show me students in danger", str(mentor.id), db)
        print("Result is:")
        print(json.dumps(res, indent=2))

import asyncio
asyncio.run(test_direct())

db.close()
