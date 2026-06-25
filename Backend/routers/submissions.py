from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from database import get_db
from models.user import User
from models.assignment import Assignment
from models.class_ import ClassMembership
from models.submission import Submission
from models.analytics import AssignmentAnalytics
from models.notification import Notification
from schemas.assignment import SubmitRequest
from utils.dependencies import require_role, verify_admin_class_access, verify_mentor_class_access
from services import analytics_service
from websocket.tracker_ws import manager
import asyncio

router = APIRouter()

@router.post("/assignments/{assignment_id}/submit", status_code=201)
def submit_assignment(assignment_id: str, req: SubmitRequest, db: Session = Depends(get_db), u: User = Depends(require_role(["STUDENT"]))):
    a = db.query(Assignment).filter_by(id=assignment_id).first()
    if not a: raise HTTPException(404, "Not found")
    if a.status != 'PUBLISHED': raise HTTPException(400, "Assignment is not open for submission")
    
    m = db.query(ClassMembership).filter_by(class_id=a.class_id, user_id=u.id, status='ACTIVE').first()
    if not m: raise HTTPException(403, "Not an active student in this class")
    
    if a.submission_type == 'FILE' and req.submission_type != 'FILE': raise HTTPException(422, "Only FILE accepted")
    if a.submission_type == 'TEXT' and req.submission_type != 'TEXT': raise HTTPException(422, "Only TEXT accepted")
    if req.submission_type not in ('FILE', 'TEXT'): raise HTTPException(422, "Invalid submission type")
    
    if req.submission_type == 'FILE' and not req.file_url: raise HTTPException(422, "file_url required")
    if req.submission_type == 'TEXT' and not req.text_answer: raise HTTPException(422, "text_answer required")
    
    is_late = False
    now = datetime.now(timezone.utc)
    if a.deadline_at and a.deadline_at < now:
        is_late = True
        
    ext = db.query(Submission).filter_by(assignment_id=a.id, student_id=u.id, is_current=True).first()
    new_version = 1
    if ext:
        ext.is_current = False
        new_version = ext.version + 1
        
    s = Submission(
        assignment_id=a.id,
        student_id=u.id,
        submission_type=req.submission_type,
        file_url=req.file_url,
        text_answer=req.text_answer,
        is_late=is_late,
        version=new_version,
        is_current=True,
        submitted_at=now
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    
    analytics_service.recompute_student_analytics(str(u.id), str(a.class_id), db)
    
    aa = db.query(AssignmentAnalytics).filter_by(assignment_id=a.id).first()
    if aa:
        sub_count = db.query(Submission).filter_by(assignment_id=a.id, is_current=True).count()
        late_count = db.query(Submission).filter_by(assignment_id=a.id, is_current=True, is_late=True).count()
        aa.submitted_count = sub_count
        aa.late_count = late_count
        if aa.total_targets > 0:
            aa.completion_rate = round(sub_count / aa.total_targets * 100, 2)
            aa.is_bottleneck = aa.completion_rate < 50
            
    db.add(Notification(
        user_id=u.id,
        notification_type='SUBMISSION_RECEIPT',
        title='Submitted',
        body=f"Assignment {a.title} submitted at {s.submitted_at.strftime('%I:%M %p on %d %b %Y')}",
        payload={"assignment_id": str(a.id)}
    ))
    db.commit()
    
    try:
        loop = asyncio.get_event_loop()
        ws_msg = {
            "event": "submission_created",
            "assignment_id": str(a.id),
            "submitted_count": aa.submitted_count if aa else 0,
            "pending_count": (aa.total_targets - aa.submitted_count) if aa else 0,
            "missed_count": 0,
            "late_count": aa.late_count if aa else 0,
            "student": {
                "student_id": str(u.id),
                "full_name": u.full_name,
                "tracker_status": "LATE" if is_late else "SUBMITTED",
                "submitted_at": s.submitted_at.isoformat() + "Z",
                "is_late": is_late
            }
        }
        if loop.is_running():
            loop.create_task(manager.broadcast(str(a.id), ws_msg))
        else:
            asyncio.run(manager.broadcast(str(a.id), ws_msg))
    except Exception:
        pass
        
    return {
        "submission_id": str(s.id),
        "submitted_at": s.submitted_at.isoformat() + "Z",
        "is_late": is_late,
        "version": new_version,
        "receipt": f"Submitted successfully at {s.submitted_at.strftime('%I:%M %p on %d %b %Y')}"
    }

@router.get("/submissions/my")
def get_my_submissions(db: Session = Depends(get_db), u: User = Depends(require_role(["STUDENT"]))):
    res = db.execute(text("""
        SELECT s.id as submission_id, s.assignment_id, a.title as assignment_title,
               s.submission_type, s.submitted_at, s.is_late, s.version
        FROM submissions s
        JOIN assignments a ON a.id = s.assignment_id
        WHERE s.student_id = :user_id AND s.is_current = true
        ORDER BY s.submitted_at DESC
    """), {"user_id": str(u.id)}).fetchall()
    
    return {"submissions": [dict(r._mapping) for r in res]}

@router.get("/assignments/{assignment_id}/submissions")
def get_submissions(assignment_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    a = db.query(Assignment).filter_by(id=assignment_id).first()
    if not a: raise HTTPException(404, "Not found")
    
    if u.role == "MENTOR":
        verify_mentor_class_access(a.class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(a.class_id, u, db)
        
    res = db.execute(text("""
        SELECT s.id as submission_id, s.student_id, u.full_name as student_name,
               s.submission_type, s.file_url, s.text_answer, s.submitted_at, s.is_late, s.version
        FROM submissions s
        JOIN users u ON u.id = s.student_id
        WHERE s.assignment_id = :assignment_id AND s.is_current = true
        ORDER BY s.submitted_at DESC
    """), {"assignment_id": assignment_id}).fetchall()
    
    return {"submissions": [dict(r._mapping) for r in res]}
