import os
from dotenv import load_dotenv
load_dotenv()

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    'default': SQLAlchemyJobStore(url=os.getenv("DATABASE_URL"))
}
scheduler = AsyncIOScheduler(jobstores=jobstores)

def close_assignment_job(assignment_id: str):
    from database import SessionLocal
    from models.assignment import Assignment
    from models.submission import Submission
    from models.class_ import ClassMembership
    from models.notification import Notification
    from services import analytics_service, fcm_service
    from websocket.tracker_ws import manager
    import asyncio

    db = SessionLocal()
    try:
        assignment = db.query(Assignment).filter_by(id=assignment_id).first()
        if not assignment or assignment.status == 'CLOSED':
            return
        assignment.status = 'CLOSED'
        db.commit()

        analytics_service.recompute_all_after_close(assignment_id, db)

        from models.user import User
        submitted_ids = {
            s.student_id for s in db.query(Submission).filter(
                Submission.assignment_id == assignment_id,
                Submission.is_current == True
            ).all()
        }
        active_students = db.query(User).join(ClassMembership).filter(
            ClassMembership.class_id == assignment.class_id,
            ClassMembership.member_role == 'STUDENT',
            ClassMembership.status == 'ACTIVE'
        ).all()

        missed_tokens = []
        for student in active_students:
            if student.id not in submitted_ids:
                db.add(Notification(
                    user_id=student.id,
                    notification_type='MISSED_DEADLINE',
                    title='Missed Deadline',
                    body=f'You missed {assignment.title}',
                    payload={"assignment_id": str(assignment_id), "class_id": str(assignment.class_id)}
                ))
                if student.fcm_token:
                    missed_tokens.append(student.fcm_token)
        db.commit()

        if missed_tokens:
            fcm_service.send_batch_fcm(missed_tokens, "Missed Deadline", f"You missed {assignment.title}")

        from models.submission import Submission as Sub
        sub_count = db.query(Sub).filter(Sub.assignment_id == assignment_id, Sub.is_current == True).count()
        late_count = db.query(Sub).filter(Sub.assignment_id == assignment_id, Sub.is_current == True, Sub.is_late == True).count()
        total_active = len(active_students)
        missed_count = total_active - sub_count

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(manager.broadcast(str(assignment_id), {
                    "event": "tracker_refresh",
                    "assignment_id": str(assignment_id),
                    "status": "CLOSED",
                    "submitted_count": sub_count,
                    "pending_count": 0,
                    "missed_count": missed_count,
                    "late_count": late_count
                }))
            else:
                asyncio.run(manager.broadcast(str(assignment_id), {
                    "event": "tracker_refresh",
                    "assignment_id": str(assignment_id),
                    "status": "CLOSED",
                    "submitted_count": sub_count,
                    "pending_count": 0,
                    "missed_count": missed_count,
                    "late_count": late_count
                }))
        except Exception:
            pass
    finally:
        db.close()

def send_reminder_job(assignment_id: str, window: str):
    from database import SessionLocal
    from models.assignment import Assignment
    from models.submission import Submission
    from models.class_ import ClassMembership
    from models.notification import Notification
    from models.user import User
    from services import fcm_service

    db = SessionLocal()
    try:
        assignment = db.query(Assignment).filter_by(id=assignment_id).first()
        if not assignment or assignment.status != 'PUBLISHED':
            return

        submitted_ids = {
            s.student_id for s in db.query(Submission).filter(
                Submission.assignment_id == assignment_id,
                Submission.is_current == True
            ).all()
        }
        pending_students = db.query(User).join(ClassMembership).filter(
            ClassMembership.class_id == assignment.class_id,
            ClassMembership.member_role == 'STUDENT',
            ClassMembership.status == 'ACTIVE'
        ).all()
        pending_students = [s for s in pending_students if s.id not in submitted_ids]

        title = "Reminder" if window == "24h" else "Final Reminder"
        body = f"{assignment.title} due tomorrow" if window == "24h" else f"{assignment.title} due in 2 hours"

        tokens = []
        for student in pending_students:
            db.add(Notification(
                user_id=student.id,
                notification_type='DEADLINE_REMINDER',
                title=title,
                body=body,
                payload={"assignment_id": str(assignment_id)}
            ))
            if student.fcm_token:
                tokens.append(student.fcm_token)
        db.commit()
        if tokens:
            fcm_service.send_batch_fcm(tokens, title, body)
    finally:
        db.close()

def send_student_reminder_job(reminder_job_id: str):
    from database import SessionLocal
    from models.notification import ReminderJob, Notification
    from models.assignment import Assignment
    from services import fcm_service

    db = SessionLocal()
    try:
        rj = db.query(ReminderJob).filter_by(id=reminder_job_id).first()
        if not rj or rj.status != 'SCHEDULED':
            return
        assignment = db.query(Assignment).filter_by(id=rj.assignment_id).first()
        db.add(Notification(
            user_id=rj.user_id,
            notification_type='DEADLINE_REMINDER',
            title='Reminder',
            body=f"Your custom reminder for: {assignment.title if assignment else 'assignment'}",
            payload={"assignment_id": str(rj.assignment_id)}
        ))
        rj.status = 'TRIGGERED'
        db.commit()
        from models.user import User
        student = db.query(User).filter_by(id=rj.user_id).first()
        if student and student.fcm_token and assignment:
            fcm_service.send_single_fcm(student.fcm_token, "Reminder", f"Don't forget: {assignment.title}")
    finally:
        db.close()
