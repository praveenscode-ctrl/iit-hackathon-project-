from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from database import get_db
from models.user import User
from models.notification import Notification, ReminderJob
from models.assignment import Assignment
from models.class_ import ClassMembership
from schemas.assignment import ReminderRequest
from utils.dependencies import require_role, get_current_user
from scheduler.jobs import scheduler, send_student_reminder_job
import dateutil.parser

router = APIRouter()

@router.get("")
def get_notifications(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    notifs = db.query(Notification).filter(Notification.user_id == u.id).order_by(Notification.created_at.desc()).all()
    unread = sum(1 for n in notifs if not n.is_read)
    return {
        "notifications": [
            {
                "id": str(n.id),
                "notification_type": n.notification_type,
                "title": n.title,
                "body": n.body,
                "payload": n.payload or {},
                "is_read": n.is_read,
                "created_at": n.created_at
            }
            for n in notifs
        ],
        "unread_count": unread
    }

# IMPORTANT: read-all MUST be before /{notification_id}/read
@router.patch("/read-all")
def mark_all_read(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == u.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}

@router.patch("/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n:
        raise HTTPException(404, "Notification not found")
    if str(n.user_id) != str(u.id):
        raise HTTPException(403, "Not your notification")
    n.is_read = True
    db.commit()
    return {"is_read": True}

@router.post("/reminder", status_code=201)
def create_reminder(req: ReminderRequest, db: Session = Depends(get_db), u: User = Depends(require_role(["STUDENT"]))):
    a = db.query(Assignment).filter_by(id=req.assignment_id).first()
    if not a: raise HTTPException(404, "Not found")
    if a.status != 'PUBLISHED': raise HTTPException(400, "Assignment must be published")
    
    m = db.query(ClassMembership).filter_by(class_id=a.class_id, user_id=u.id, status='ACTIVE').first()
    if not m: raise HTTPException(403, "Not an active student in this class")
    
    dt = dateutil.parser.isoparse(req.remind_at)
    if dt < datetime.now(timezone.utc):
        raise HTTPException(400, "remind_at must be in the future")
        
    rj = ReminderJob(
        user_id=u.id,
        assignment_id=a.id,
        remind_at=dt,
        status='SCHEDULED'
    )
    db.add(rj)
    db.commit()
    db.refresh(rj)
    
    scheduler.add_job(send_student_reminder_job, 'date', run_date=dt, args=[str(rj.id)], id=f"student_reminder_{rj.id}", replace_existing=True)
    
    return {"reminder_id": str(rj.id), "remind_at": rj.remind_at.isoformat() + "Z"}

