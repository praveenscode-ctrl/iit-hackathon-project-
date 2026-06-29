from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from scheduler.jobs import scheduler
from datetime import datetime

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all tables are created in the database
    from database import Base, engine
    from models import user, submission, notification, export, class_, bulk_import, assignment, analytics
    Base.metadata.create_all(bind=engine)

    # Ensure constraints and columns are updated in PostgreSQL / SQLite
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            if "postgresql" in engine.dialect.name:
                conn.execute(text("ALTER TABLE student_analytics DROP CONSTRAINT IF EXISTS check_sa_risk;"))
                conn.execute(text("ALTER TABLE student_analytics ADD CONSTRAINT check_sa_risk CHECK (risk_level IN ('NORMAL', 'LOW', 'MEDIUM', 'HIGH', 'RECOVERING', 'CRITICAL'));"))
                
                # Update check_notif_type check constraint
                conn.execute(text("ALTER TABLE notifications DROP CONSTRAINT IF EXISTS check_notif_type;"))
                conn.execute(text("ALTER TABLE notifications ADD CONSTRAINT check_notif_type CHECK (notification_type IN ('STUDENT_APPROVED', 'STUDENT_REJECTED', 'ASSIGNMENT_PUBLISHED', 'DEADLINE_REMINDER', 'SUBMISSION_RECEIPT', 'MISSED_DEADLINE', 'RISK_ALERT', 'CO_MENTOR_ADDED', 'CLASS_ARCHIVED', 'LATE_SUBMISSION_REASON'));"))
                
                # Check and add late_reason column to submissions
                col_check = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='submissions' AND column_name='late_reason';")).first()
                if not col_check:
                    conn.execute(text("ALTER TABLE submissions ADD COLUMN late_reason TEXT;"))
                conn.commit()
            else:
                # SQLite
                try:
                    conn.execute(text("ALTER TABLE submissions ADD COLUMN late_reason TEXT;"))
                    conn.commit()
                except Exception:
                    pass
    except Exception as e:
        print("Auto database updates bypassed:", e)

    if not scheduler.running:
        scheduler.start()
    yield
    # Note: for test suites this might get tricky, but FastAPI handles lifespan per TestClient block
    # Actually just letting it run or shutting down conditionally
    if scheduler.running:
        # We can pass wait=False to not block tests
        scheduler.shutdown(wait=False)

app = FastAPI(title="AssignHub API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

from routers.auth import router as auth_router
from routers.classes import router as class_router
from routers.provisioning import router as provision_router
from routers.assignments import router as assignment_router
from routers.submissions import router as submission_router
from routers.storage import router as storage_router
from routers.notifications import router as notification_router
from routers.analytics import router as analytics_router
from routers.exports import router as exports_router
from routers.ai_query import router as ai_query_router
from websocket.tracker_ws import ws_router

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(class_router, prefix="/api/v1/classes", tags=["Classes"])
app.include_router(provision_router, prefix="/api/v1/provision", tags=["Provisioning"])
app.include_router(assignment_router, prefix="/api/v1/assignments", tags=["Assignments"])
app.include_router(submission_router, prefix="/api/v1", tags=["Submissions"])
app.include_router(storage_router, prefix="/api/v1/storage", tags=["Storage"])
app.include_router(notification_router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(exports_router, prefix="/api/v1/exports", tags=["Exports"])
app.include_router(ai_query_router, prefix="/api/v1/ai", tags=["AI Query"])
app.include_router(ws_router)

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}
