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
from schemas.assignment import SubmitRequest, ExtensionRequestCreate
from utils.dependencies import require_role, verify_admin_class_access, verify_mentor_class_access
from services import analytics_service
from websocket.tracker_ws import manager
import asyncio

router = APIRouter()

@router.post("/assignments/{assignment_id}/submit", status_code=201)
async def submit_assignment(assignment_id: str, req: SubmitRequest, db: Session = Depends(get_db), u: User = Depends(require_role(["STUDENT"]))):
    a = db.query(Assignment).filter_by(id=assignment_id).first()
    if not a: raise HTTPException(404, "Not found")
    if a.status == 'DRAFT': raise HTTPException(400, "Assignment is not open for submission")
    
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
        
    resolved_reason = req.late_reason
    if a.status == 'CLOSED' or is_late:
        is_late = True
        # Verify student has an APPROVED extension request
        from models.submission import ExtensionRequest
        ext_req = db.query(ExtensionRequest).filter_by(
            assignment_id=a.id,
            student_id=u.id,
            status='APPROVED'
        ).first()
        if not ext_req:
            raise HTTPException(
                status_code=403,
                detail="Assignment deadline has passed or it is closed. You must request and receive approval from your mentor before submitting."
            )
        resolved_reason = ext_req.reason
        
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
        late_reason=resolved_reason,
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
            aa.is_bottleneck = aa.completion_rate < 40.0
            
    db.add(Notification(
        user_id=u.id,
        notification_type='SUBMISSION_RECEIPT',
        title='Submitted',
        body=f"Assignment {a.title} submitted at {s.submitted_at.strftime('%I:%M %p on %d %b %Y')}",
        payload={"assignment_id": str(a.id)}
    ))
    
    if is_late and req.late_reason:
        mentors = db.query(User).join(ClassMembership).filter(
            ClassMembership.class_id == a.class_id,
            ClassMembership.member_role == 'MENTOR',
            ClassMembership.status == 'ACTIVE'
        ).all()
        for mentor in mentors:
            db.add(Notification(
                user_id=mentor.id,
                notification_type='LATE_SUBMISSION_REASON',
                title='Late Submission Reason',
                body=f"Student {u.full_name} submitted late for '{a.title}' due to: {req.late_reason}",
                payload={"assignment_id": str(a.id), "student_id": str(u.id), "late_reason": req.late_reason}
            ))
            
    db.commit()
    
    try:
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
                "submitted_at": s.submitted_at.isoformat(),
                "is_late": is_late
            }
        }
        await manager.broadcast(str(a.id), ws_msg)
    except Exception as e:
        print("Submission WebSocket broadcast failed:", e)
        
    return {
        "submission_id": str(s.id),
        "submitted_at": s.submitted_at.isoformat(),
        "is_late": is_late,
        "version": new_version,
        "receipt": f"Submitted successfully at {s.submitted_at.strftime('%I:%M %p on %d %b %Y')}"
    }

@router.get("/submissions/my")
def get_my_submissions(db: Session = Depends(get_db), u: User = Depends(require_role(["STUDENT"]))):
    res = db.execute(text("""
        SELECT s.id as submission_id, s.assignment_id, a.title as assignment_title,
               s.submission_type, s.file_url, s.text_answer, s.submitted_at, s.is_late, s.version, s.late_reason
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
        SELECT s.id, s.student_id, u.full_name, u.registration_id,
               s.submission_type, s.file_url, s.text_answer, s.submitted_at, s.is_late, s.version, s.late_reason
        FROM submissions s
        JOIN users u ON u.id = s.student_id
        WHERE s.assignment_id = :assignment_id AND s.is_current = true
        ORDER BY s.submitted_at DESC
    """), {"assignment_id": assignment_id}).fetchall()
    
    submissions_list = []
    for r in res:
        submissions_list.append({
            "id": str(r.id),
            "student_id": str(r.student_id),
            "student": {
                "full_name": r.full_name,
                "registration_id": r.registration_id
            },
            "submission_type": r.submission_type,
            "file_url": r.file_url,
            "text_answer": r.text_answer,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "is_late": r.is_late,
            "late_reason": r.late_reason,
            "version": r.version
        })
    return {"submissions": submissions_list}

@router.post("/assignments/{assignment_id}/extension-request", status_code=201)
def request_extension(
    assignment_id: str,
    req: ExtensionRequestCreate,
    db: Session = Depends(get_db),
    u: User = Depends(require_role(["STUDENT"]))
):
    from models.submission import ExtensionRequest
    a = db.query(Assignment).filter_by(id=assignment_id).first()
    if not a: raise HTTPException(404, "Assignment not found")
    
    # Check if they are in the class
    m = db.query(ClassMembership).filter_by(class_id=a.class_id, user_id=u.id, status='ACTIVE').first()
    if not m: raise HTTPException(403, "Not an active student in this class")
    
    # Check if there is already a request
    existing = db.query(ExtensionRequest).filter_by(assignment_id=a.id, student_id=u.id).first()
    if existing:
        raise HTTPException(400, "You have already requested an extension for this assignment")
        
    er = ExtensionRequest(
        assignment_id=a.id,
        student_id=u.id,
        reason=req.reason,
        status='PENDING'
    )
    db.add(er)
    db.commit()
    db.refresh(er)
    
    # Notify mentors
    mentors = db.query(User).join(ClassMembership).filter(
        ClassMembership.class_id == a.class_id,
        ClassMembership.member_role == 'MENTOR',
        ClassMembership.status == 'ACTIVE'
    ).all()
    for mentor in mentors:
        db.add(Notification(
            user_id=mentor.id,
            notification_type='EXTENSION_REQUESTED',
            title='Late Submission Request',
            body=f"Student {u.full_name} requested a late submission for '{a.title}' due to: {req.reason}",
            payload={"assignment_id": str(a.id), "student_id": str(u.id), "request_id": str(er.id)}
        ))
    db.commit()
    
    return {"id": str(er.id), "status": er.status}

@router.get("/assignments/{assignment_id}/extension-requests")
def get_extension_requests(
    assignment_id: str,
    db: Session = Depends(get_db),
    u: User = Depends(require_role(["ADMIN", "MENTOR"]))
):
    from models.submission import ExtensionRequest
    a = db.query(Assignment).filter_by(id=assignment_id).first()
    if not a: raise HTTPException(404, "Assignment not found")
    
    if u.role == "MENTOR":
        verify_mentor_class_access(a.class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(a.class_id, u, db)
        
    reqs = db.query(ExtensionRequest, User.full_name, User.registration_id).join(
        User, ExtensionRequest.student_id == User.id
    ).filter(ExtensionRequest.assignment_id == a.id).all()
    
    return {
        "requests": [
            {
                "id": str(r[0].id),
                "student_id": str(r[0].student_id),
                "student_name": r[1],
                "registration_id": r[2],
                "reason": r[0].reason,
                "status": r[0].status,
                "created_at": r[0].created_at
            }
            for r in reqs
        ]
    }

@router.post("/extension-requests/{request_id}/approve")
def approve_extension(
    request_id: str,
    db: Session = Depends(get_db),
    u: User = Depends(require_role(["ADMIN", "MENTOR"]))
):
    from models.submission import ExtensionRequest
    er = db.query(ExtensionRequest).filter_by(id=request_id).first()
    if not er: raise HTTPException(404, "Request not found")
    
    a = db.query(Assignment).filter_by(id=er.assignment_id).first()
    if u.role == "MENTOR":
        verify_mentor_class_access(a.class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(a.class_id, u, db)
        
    er.status = 'APPROVED'
    db.commit()
    
    # Notify student
    db.add(Notification(
        user_id=er.student_id,
        notification_type='EXTENSION_APPROVED',
        title='Late Submission Request Approved',
        body=f"Your request to submit '{a.title}' late has been APPROVED by your mentor. You can now submit your assignment.",
        payload={"assignment_id": str(a.id)}
    ))
    db.commit()
    
    return {"id": str(er.id), "status": er.status}

@router.post("/extension-requests/{request_id}/reject")
def reject_extension(
    request_id: str,
    db: Session = Depends(get_db),
    u: User = Depends(require_role(["ADMIN", "MENTOR"]))
):
    from models.submission import ExtensionRequest
    er = db.query(ExtensionRequest).filter_by(id=request_id).first()
    if not er: raise HTTPException(404, "Request not found")
    
    a = db.query(Assignment).filter_by(id=er.assignment_id).first()
    if u.role == "MENTOR":
        verify_mentor_class_access(a.class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(a.class_id, u, db)
        
    er.status = 'REJECTED'
    db.commit()
    
    # Notify student
    db.add(Notification(
        user_id=er.student_id,
        notification_type='EXTENSION_REJECTED',
        title='Late Submission Request Rejected',
        body=f"Your request to submit '{a.title}' late was rejected/put on wait.",
        payload={"assignment_id": str(a.id)}
    ))
    db.commit()
    
    return {"id": str(er.id), "status": er.status}
