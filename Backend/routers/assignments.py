from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timezone, timedelta
from database import get_db
from models.user import User
from models.assignment import Assignment
from models.class_ import ClassMembership
from models.analytics import AssignmentAnalytics
from models.notification import Notification
from schemas.assignment import CreateAssignmentRequest
from utils.dependencies import require_role, verify_admin_class_access, verify_mentor_class_access
from services import fcm_service, analytics_service
from scheduler.jobs import scheduler, close_assignment_job, send_reminder_job
import dateutil.parser

router = APIRouter()

@router.post("", status_code=201)
def create_assignment(req: CreateAssignmentRequest, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    if req.content_type not in ('PDF', 'LINK', 'RICH_TEXT'):
        raise HTTPException(422, "Invalid content_type")
    if req.submission_type not in ('FILE', 'TEXT', 'BOTH'):
        raise HTTPException(422, "Invalid submission_type")

    if u.role == "MENTOR":
        verify_mentor_class_access(req.class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(req.class_id, u, db)

    dt = None
    if req.deadline_at:
        dt = dateutil.parser.isoparse(req.deadline_at)

    a = Assignment(
        class_id=req.class_id,
        created_by=u.id,
        title=req.title,
        description=req.description,
        content_type=req.content_type,
        content_url=req.content_url,
        rich_text_body=req.rich_text_body,
        submission_type=req.submission_type,
        deadline_at=dt,
        auto_close=req.auto_close,
        status='DRAFT'
    )
    db.add(a)
    db.commit()
    db.refresh(a)

    return {"id": str(a.id), "title": a.title, "status": a.status, "deadline_at": a.deadline_at, "created_at": a.created_at}

@router.get("")
def get_assignments(class_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR", "STUDENT"]))):
    if u.role == "STUDENT":
        m = db.query(ClassMembership).filter_by(class_id=class_id, user_id=u.id, status='ACTIVE').first()
        if not m: raise HTTPException(403, "Not an active student")
    elif u.role == "MENTOR":
        verify_mentor_class_access(class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(class_id, u, db)

    q = db.query(Assignment, User.full_name).join(User, Assignment.created_by == User.id).filter(Assignment.class_id == class_id)
    if u.role == "STUDENT":
        q = q.filter(Assignment.status.in_(['PUBLISHED', 'CLOSED']))

    res = []
    for a, creator in q.all():
        d = {c.name: getattr(a, c.name) for c in a.__table__.columns}
        d["id"] = str(d["id"])
        d["class_id"] = str(d["class_id"])
        d["created_by"] = str(d["created_by"])
        d["created_by_name"] = creator
        
        if u.role == "STUDENT":
            from models.submission import Submission
            s = db.query(Submission).filter_by(assignment_id=a.id, student_id=u.id, is_current=True).first()
            if s:
                d["student_submission"] = {
                    "submitted": True,
                    "submission_id": str(s.id),
                    "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
                    "is_late": s.is_late,
                    "version": s.version
                }
            else:
                d["student_submission"] = None
        else:
            d["student_submission"] = None

        res.append(d)

    return {"assignments": res}

@router.get("/{assignment_id}")
def get_assignment(assignment_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR", "STUDENT"]))):
    row = db.query(Assignment, User.full_name).join(User, Assignment.created_by == User.id).filter(Assignment.id == assignment_id).first()
    if not row: raise HTTPException(404, "Not found")
    a, creator = row

    if u.role == "STUDENT":
        if a.status not in ('PUBLISHED', 'CLOSED'): raise HTTPException(404, "Not found")
        m = db.query(ClassMembership).filter_by(class_id=a.class_id, user_id=u.id, status='ACTIVE').first()
        if not m: raise HTTPException(403, "Not an active student")

    sub_info = {"submitted": False, "submission_id": None, "submitted_at": None, "is_late": False, "version": 0}
    if u.role == "STUDENT":
        from models.submission import Submission
        s = db.query(Submission).filter_by(assignment_id=a.id, student_id=u.id, is_current=True).first()
        if s:
            sub_info = {"submitted": True, "submission_id": str(s.id), "submitted_at": s.submitted_at, "is_late": s.is_late, "version": s.version}

    d = {c.name: getattr(a, c.name) for c in a.__table__.columns}
    d["id"] = str(d["id"])
    d["class_id"] = str(d["class_id"])
    d["created_by"] = str(d["created_by"])
    d["created_by_name"] = creator
    d["student_submission"] = sub_info
    return d

@router.post("/{assignment_id}/publish")
def publish_assignment(assignment_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    a = db.query(Assignment).filter_by(id=assignment_id).first()
    if not a: raise HTTPException(404, "Not found")
    if a.status != 'DRAFT': raise HTTPException(409, "Assignment already published or closed")

    if u.role == "MENTOR":
        verify_mentor_class_access(a.class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(a.class_id, u, db)

    a.status = 'PUBLISHED'
    a.updated_at = datetime.utcnow()
    
    total_targets = db.query(ClassMembership).filter_by(class_id=a.class_id, member_role='STUDENT', status='ACTIVE').count()
    db.add(AssignmentAnalytics(assignment_id=a.id, total_targets=total_targets, submitted_count=0, missed_count=0, late_count=0, completion_rate=0.0, is_bottleneck=False))
    
    students = db.query(User).join(ClassMembership).filter(ClassMembership.class_id == a.class_id, ClassMembership.member_role == 'STUDENT', ClassMembership.status == 'ACTIVE').all()
    tokens = []
    
    for s in students:
        db.add(Notification(user_id=s.id, notification_type='ASSIGNMENT_PUBLISHED', title='New Assignment', body=a.title, payload={"assignment_id": str(a.id)}))
        if s.fcm_token: tokens.append(s.fcm_token)
        analytics_service.recompute_student_analytics(str(s.id), str(a.class_id), db)
    
    db.commit()
    
    dl_str = "No deadline"
    if a.deadline_at:
        dl_str = str(a.deadline_at)
        scheduler.add_job(close_assignment_job, 'date', run_date=a.deadline_at, args=[str(a.id)], id=f"close_{a.id}", replace_existing=True)
        scheduler.add_job(send_reminder_job, 'date', run_date=a.deadline_at - timedelta(hours=24), args=[str(a.id), "24h"], id=f"remind_24h_{a.id}", replace_existing=True)
        scheduler.add_job(send_reminder_job, 'date', run_date=a.deadline_at - timedelta(hours=2), args=[str(a.id), "2h"], id=f"remind_2h_{a.id}", replace_existing=True)

    if tokens:
        fcm_service.send_batch_fcm(tokens, "New Assignment", f"{a.title} — due {dl_str}", db=db)

    return {"status": "PUBLISHED", "message": "Assignment published and students notified"}

@router.post("/{assignment_id}/close")
def close_assignment(assignment_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    a = db.query(Assignment).filter_by(id=assignment_id).first()
    if not a: raise HTTPException(404, "Not found")
    
    if u.role == "MENTOR":
        verify_mentor_class_access(a.class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(a.class_id, u, db)

    a.status = 'CLOSED'
    a.updated_at = datetime.utcnow()
    db.commit()

    analytics_service.recompute_all_after_close(str(a.id), db)
    return {"status": "CLOSED"}

@router.get("/{assignment_id}/tracker")
def tracker(assignment_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    a = db.query(Assignment).filter_by(id=assignment_id).first()
    if not a: raise HTTPException(404, "Not found")
    
    if u.role == "MENTOR":
        verify_mentor_class_access(a.class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(a.class_id, u, db)

    query = """
    SELECT 
        u.id as student_id,
        u.full_name,
        u.email,
        u.registration_id,
        sa.risk_level,
        CASE 
            WHEN s.id IS NOT NULL AND s.is_late = false THEN 'SUBMITTED'
            WHEN s.id IS NOT NULL AND s.is_late = true THEN 'LATE'
            WHEN a.status = 'CLOSED' AND s.id IS NULL THEN 'MISSED'
            ELSE 'PENDING'
        END as tracker_status,
        s.id as submission_id,
        s.submitted_at,
        s.is_late,
        s.version
    FROM class_memberships cm
    JOIN users u ON cm.user_id = u.id
    CROSS JOIN assignments a
    LEFT JOIN submissions s ON s.student_id = u.id AND s.assignment_id = a.id AND s.is_current = true
    LEFT JOIN student_analytics sa ON sa.student_id = u.id AND sa.class_id = cm.class_id
    WHERE cm.class_id = :class_id
      AND cm.member_role = 'STUDENT'
      AND cm.status = 'ACTIVE'
      AND a.id = :assignment_id
    """
    
    rows = db.execute(text(query), {"class_id": str(a.class_id), "assignment_id": assignment_id}).fetchall()
    
    counts = {"SUBMITTED": 0, "LATE": 0, "MISSED": 0, "PENDING": 0}
    students = []
    
    for r in rows:
        st = r.tracker_status
        counts[st] += 1
        students.append({
            "student_id": str(r.student_id),
            "full_name": r.full_name,
            "email": r.email,
            "registration_id": r.registration_id,
            "risk_level": r.risk_level or "NORMAL",
            "tracker_status": st,
            "submission_id": str(r.submission_id) if r.submission_id else None,
            "submitted_at": r.submitted_at,
            "is_late": r.is_late if r.is_late is not None else False,
            "version": r.version or 0
        })

    return {
        "assignment_id": str(a.id),
        "title": a.title,
        "deadline_at": a.deadline_at,
        "status": a.status,
        "submitted_count": counts["SUBMITTED"] + counts["LATE"],
        "pending_count": counts["PENDING"],
        "missed_count": counts["MISSED"],
        "late_count": counts["LATE"],
        "students": students
    }
