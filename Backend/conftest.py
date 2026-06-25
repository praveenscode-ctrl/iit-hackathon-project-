import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from dotenv import load_dotenv
from unittest.mock import patch

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from database import Base, get_db
from main import app

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    with patch("scheduler.jobs.scheduler.start"), patch("scheduler.jobs.scheduler.shutdown"), patch("websocket.tracker_ws.manager.broadcast"):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def admin_token(client, db):
    with patch("services.email_service.send_otp_email"):
        client.post("/api/v1/auth/admin/signup", json={
            "full_name": "Test Admin",
            "email": "admin@conftest.com",
            "password": "Test1234!"
        })
    from models.user import OtpVerification
    otp_row = db.query(OtpVerification).filter_by(email="admin@conftest.com").first()
    resp = client.post("/api/v1/auth/admin/verify-otp", json={
        "email": "admin@conftest.com",
        "otp": otp_row.otp_code
    })
    return resp.json()["access_token"]

@pytest.fixture(scope="function")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
