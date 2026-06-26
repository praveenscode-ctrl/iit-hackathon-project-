from sqlalchemy.orm import Session
from sqlalchemy import func
from models.analytics import StudentAnalytics, AssignmentAnalytics, ClassAnalytics
from models.submission import Submission
from models.assignment import Assignment
from models.class_ import ClassMembership
from models.notification import Notification
from services import fcm_service
from datetime import datetime, timezone
import uuid

def send_risk_alert(student_id: str, db: Session):
    from models.user import User
    student = db.query(User).filter_by(id=student_id).first()
    if not student: return
    
    sa = db.query(StudentAnalytics).filter_by(student_id=student_id).first()
    class_id_str = str(sa.class_id) if sa else None

    n = Notification(
        user_id=student.id,
        notification_type='RISK_ALERT',
        title='Risk Alert',
        body='Your academic standing is marked as HIGH RISK due to consecutive missed assignments. Please contact your mentor immediately.',
        payload={"class_id": class_id_str, "assignment_id": None}
    )
    db.add(n)
    if student.fcm_token:
        fcm_service.send_single_fcm(student.fcm_token, n.title, n.body)

def recompute_student_analytics(student_id: str, class_id: str, db: Session):
    active_assignments = db.query(Assignment).filter(
        Assignment.class_id == class_id,
        Assignment.status.in_(['PUBLISHED', 'CLOSED'])
    ).order_by(Assignment.created_at.asc()).all()
    
    closed_assignments = [a for a in active_assignments if a.status == 'CLOSED']
    
    sa = db.query(StudentAnalytics).filter_by(student_id=student_id, class_id=class_id).first()
    prev_risk = sa.risk_level if sa else 'NORMAL'
    
    if not sa:
        sa = StudentAnalytics(student_id=student_id, class_id=class_id)
        db.add(sa)
        db.flush()

    total_assigned = len(active_assignments)
    
    if total_assigned == 0:
        sa.total_assigned = 0
        sa.total_submitted = 0
        sa.total_missed = 0
        sa.total_late = 0
        sa.completion_rate = 0.0
        sa.current_streak = 0
        sa.longest_streak = 0
        sa.consecutive_misses = 0
        sa.avg_submission_delay_hours = None
        sa.risk_level = 'NORMAL'
        sa.last_computed_at = datetime.now(timezone.utc)
        db.commit()
        return

    all_assignment_ids = [a.id for a in active_assignments]
    submissions = db.query(Submission).filter(
        Submission.student_id == student_id,
        Submission.assignment_id.in_(all_assignment_ids),
        Submission.is_current == True
    ).all()
    
    submitted_ids = {s.assignment_id: s for s in submissions}
    
    total_submitted = len(submitted_ids)
    total_missed = sum(1 for a in closed_assignments if a.id not in submitted_ids)
    total_late = sum(1 for s in submissions if s.is_late)
    completion_rate = round((total_submitted / total_assigned) * 100, 2)
    
    # Streaks (process from oldest to newest)
    longest_streak = 0
    current_run = 0
    for a in closed_assignments:
        if a.id in submitted_ids:
            current_run += 1
            longest_streak = max(longest_streak, current_run)
        else:
            current_run = 0
            
    # Process from newest to oldest for current metrics
    sorted_desc = sorted(closed_assignments, key=lambda x: x.created_at, reverse=True)
    
    current_streak = 0
    for a in sorted_desc:
        if a.id in submitted_ids:
            current_streak += 1
        else:
            break
            
    consecutive_misses = 0
    for a in sorted_desc:
        if a.id not in submitted_ids:
            consecutive_misses += 1
        else:
            break

    delays = []
    for a in closed_assignments:
        if a.id in submitted_ids and a.deadline_at:
            s = submitted_ids[a.id]
            delay_sec = (s.submitted_at - a.deadline_at.replace(tzinfo=timezone.utc)).total_seconds()
            delays.append(delay_sec / 3600.0)
            
    avg_delay = round(sum(delays) / len(delays), 2) if delays else None
    
    if consecutive_misses >= 4:
        risk_level = 'CRITICAL'
    elif consecutive_misses >= 3:
        risk_level = 'HIGH'
    elif completion_rate < 40:
        risk_level = 'MEDIUM'
    elif completion_rate < 60:
        risk_level = 'LOW'
    elif prev_risk in ('HIGH', 'CRITICAL') and completion_rate >= 60:
        risk_level = 'RECOVERING'
    else:
        risk_level = 'NORMAL'

    sa.total_assigned = total_assigned
    sa.total_submitted = total_submitted
    sa.total_missed = max(0, total_missed)
    sa.total_late = total_late
    sa.completion_rate = completion_rate
    sa.current_streak = current_streak
    sa.longest_streak = longest_streak
    sa.consecutive_misses = consecutive_misses
    sa.avg_submission_delay_hours = avg_delay
    sa.risk_level = risk_level
    sa.last_computed_at = datetime.now(timezone.utc)
    
    db.commit()
    recompute_class_analytics(class_id, db)
    
    if risk_level == 'HIGH' and prev_risk != 'HIGH':
        send_risk_alert(student_id, db)

def recompute_class_analytics(class_id: str, db: Session):
    ca = db.query(ClassAnalytics).filter_by(class_id=class_id).first()
    if not ca:
        ca = ClassAnalytics(class_id=class_id)
        db.add(ca)
        
    students = db.query(StudentAnalytics).filter_by(class_id=class_id).all()
    total_students = len(students)
    
    if total_students == 0:
        ca.total_students = 0
        ca.avg_completion = 0.0
        ca.avg_miss_rate = 0.0
        ca.avg_late_rate = 0.0
        ca.high_risk_count = 0
        ca.medium_risk_count = 0
        ca.low_risk_count = 0
        ca.last_computed_at = datetime.now(timezone.utc)
        db.commit()
        return

    ca.total_students = total_students
    
    total_assignments = db.query(Assignment).filter(
        Assignment.class_id == class_id,
        Assignment.status.in_(['PUBLISHED', 'CLOSED'])
    ).count()
    ca.total_assignments = total_assignments

    ca.avg_completion = round(sum(s.completion_rate for s in students) / total_students, 2)
    
    # Calculate averages based on total_assigned for each student
    miss_rates = []
    late_rates = []
    for s in students:
        if s.total_assigned > 0:
            miss_rates.append(s.total_missed / s.total_assigned)
            late_rates.append(s.total_late / s.total_assigned)
            
    ca.avg_miss_rate = round(sum(miss_rates) / len(miss_rates) * 100, 2) if miss_rates else 0.0
    ca.avg_late_rate = round(sum(late_rates) / len(late_rates) * 100, 2) if late_rates else 0.0
    
    ca.high_risk_count = sum(1 for s in students if s.risk_level == 'HIGH')
    ca.medium_risk_count = sum(1 for s in students if s.risk_level == 'MEDIUM')
    ca.low_risk_count = sum(1 for s in students if s.risk_level == 'LOW')
    ca.last_computed_at = datetime.now(timezone.utc)
    db.commit()

def recompute_all_after_close(assignment_id: str, db: Session):
    a = db.query(Assignment).filter_by(id=assignment_id).first()
    if not a:
        return
        
    aa = db.query(AssignmentAnalytics).filter_by(assignment_id=assignment_id).first()
    if not aa:
        aa = AssignmentAnalytics(assignment_id=assignment_id)
        db.add(aa)
        
    total_targets = db.query(ClassMembership).filter_by(class_id=a.class_id, member_role='STUDENT', status='ACTIVE').count()
    sub_count = db.query(Submission).filter_by(assignment_id=assignment_id, is_current=True).count()
    late_count = db.query(Submission).filter_by(assignment_id=assignment_id, is_current=True, is_late=True).count()
    
    aa.total_targets = total_targets
    aa.submitted_count = sub_count
    aa.late_count = late_count
    aa.missed_count = max(0, total_targets - sub_count)
    if total_targets > 0:
        aa.completion_rate = round((sub_count / total_targets) * 100, 2)
    else:
        aa.completion_rate = 0.0
        
    # Bottleneck detection: < 40% completion rate when closed
    aa.is_bottleneck = (aa.completion_rate < 40.0)
    aa.last_computed_at = datetime.now(timezone.utc)
    
    # recompute all students in this class
    students = db.query(ClassMembership).filter_by(class_id=a.class_id, member_role='STUDENT', status='ACTIVE').all()
    for st in students:
        recompute_student_analytics(str(st.user_id), str(a.class_id), db)
        
    recompute_class_analytics(str(a.class_id), db)
    db.commit()

def recompute_class_assignments_analytics(class_id: str, db: Session):
    assignments = db.query(Assignment).filter(
        Assignment.class_id == class_id,
        Assignment.status.in_(['PUBLISHED', 'CLOSED'])
    ).all()
    
    for a in assignments:
        aa = db.query(AssignmentAnalytics).filter_by(assignment_id=a.id).first()
        if not aa:
            aa = AssignmentAnalytics(assignment_id=a.id)
            db.add(aa)
            
        total_targets = db.query(ClassMembership).filter_by(class_id=class_id, member_role='STUDENT', status='ACTIVE').count()
        sub_count = db.query(Submission).filter_by(assignment_id=a.id, is_current=True).count()
        late_count = db.query(Submission).filter_by(assignment_id=a.id, is_current=True, is_late=True).count()
        
        aa.total_targets = total_targets
        aa.submitted_count = sub_count
        aa.late_count = late_count
        if a.status == 'CLOSED':
            aa.missed_count = max(0, total_targets - sub_count)
        else:
            aa.missed_count = 0
            
        if total_targets > 0:
            aa.completion_rate = round((sub_count / total_targets) * 100, 2)
        else:
            aa.completion_rate = 0.0
            
        aa.is_bottleneck = (aa.completion_rate < 40.0)
        aa.last_computed_at = datetime.now(timezone.utc)
    db.commit()
