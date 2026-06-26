from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from models.user import User
from models.analytics import StudentAnalytics, ClassAnalytics, AssignmentAnalytics
from models.class_ import ClassMembership, Class
from models.assignment import Assignment
from utils.dependencies import require_role, verify_mentor_class_access, verify_admin_class_access
from schemas.analytics import StudentAnalyticsResponse, ClassAnalyticsResponse, AdminOverviewResponse

router = APIRouter()

@router.get("/students/{student_id}")
def get_student_analytics(student_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR", "STUDENT"]))):
    if u.role == "STUDENT" and str(u.id) != student_id:
        raise HTTPException(403, "Can only view your own analytics")
        
    sa = db.query(StudentAnalytics).filter_by(student_id=student_id).first()
    if not sa:
        membership = db.query(ClassMembership).filter_by(user_id=student_id, member_role='STUDENT').first()
        if not membership:
            raise HTTPException(404, "Student analytics / membership not found")
        sa = StudentAnalytics(student_id=student_id, class_id=membership.class_id)
        db.add(sa)
        db.flush()
        
    if u.role == "MENTOR":
        verify_mentor_class_access(str(sa.class_id), u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(str(sa.class_id), u, db)

    from services.analytics_service import recompute_student_analytics
    recompute_student_analytics(student_id, str(sa.class_id), db)
        
    query = text("""
        SELECT sa.*, c.class_name, u.full_name,
          (SELECT COALESCE(AVG(sa2.completion_rate), 0) FROM student_analytics sa2 WHERE sa2.class_id = sa.class_id) as class_avg_completion
        FROM student_analytics sa
        JOIN classes c ON c.id = sa.class_id
        JOIN users u ON u.id = sa.student_id
        WHERE sa.student_id = :student_id
    """)
    r = db.execute(query, {"student_id": student_id}).fetchone()
    
    hist_query = text("""
        SELECT a.id as assignment_id, a.title, a.deadline_at,
          CASE
            WHEN s.id IS NOT NULL AND s.is_late = false THEN 'SUBMITTED'
            WHEN s.id IS NOT NULL AND s.is_late = true THEN 'LATE'
            WHEN s.id IS NULL AND a.status = 'CLOSED' THEN 'MISSED'
            ELSE 'PENDING'
          END as tracker_status,
          s.submitted_at, s.is_late
        FROM assignments a
        LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = :student_id AND s.is_current = true
        WHERE a.class_id = :class_id AND a.status IN ('PUBLISHED', 'CLOSED')
        ORDER BY a.created_at DESC
    """)
    hist_rows = db.execute(hist_query, {"student_id": student_id, "class_id": str(sa.class_id)}).fetchall()
    
    hist = []
    for hr in hist_rows:
        hist.append({
            "assignment_id": str(hr.assignment_id),
            "title": hr.title,
            "deadline_at": hr.deadline_at,
            "tracker_status": hr.tracker_status,
            "submitted_at": hr.submitted_at,
            "is_late": hr.is_late if hr.is_late is not None else False
        })
        
    return {
        "student_id": str(r.student_id),
        "full_name": r.full_name,
        "class_id": str(r.class_id),
        "class_name": r.class_name,
        "total_assigned": r.total_assigned,
        "total_submitted": r.total_submitted,
        "total_missed": r.total_missed,
        "total_late": r.total_late,
        "completion_rate": float(r.completion_rate),
        "current_streak": r.current_streak,
        "longest_streak": r.longest_streak,
        "avg_submission_delay_hours": float(r.avg_submission_delay_hours) if r.avg_submission_delay_hours is not None else None,
        "risk_level": r.risk_level,
        "consecutive_misses": r.consecutive_misses,
        "class_avg_completion": float(r.class_avg_completion),
        "assignment_history": hist,
        "last_computed_at": r.last_computed_at
    }

@router.get("/classes/{class_id}")
def get_class_analytics(class_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    if u.role == "MENTOR":
        verify_mentor_class_access(class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(class_id, u, db)
        
    # Get class name
    c = db.query(Class).filter_by(id=class_id).first()
    class_name = c.class_name if c else "Unknown"

    ca = db.query(ClassAnalytics).filter_by(class_id=class_id).first()
    if not ca:
        # Return empty state if not computed yet
        return {
            "class_id": class_id, "class_name": class_name, "total_students": 0, 
            "total_assignments": 0, "avg_completion": 0.0,
            "avg_miss_rate": 0.0, "avg_late_rate": 0.0,
            "high_risk_count": 0, "medium_risk_count": 0, "low_risk_count": 0,
            "last_computed_at": None, "risk_distribution": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NORMAL": 0, "RECOVERING": 0},
            "bottleneck_assignments": []
        }
        
    # Get risk distribution
    students = db.query(StudentAnalytics).filter_by(class_id=class_id).all()
    dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NORMAL": 0, "RECOVERING": 0}
    for s in students:
        dist[s.risk_level] += 1
        
    # Get bottleneck assignments
    bottlenecks = db.query(AssignmentAnalytics, Assignment.title).join(
        Assignment, AssignmentAnalytics.assignment_id == Assignment.id
    ).filter(
        Assignment.class_id == class_id,
        AssignmentAnalytics.is_bottleneck == True
    ).all()
    
    b_list = []
    for ba, title in bottlenecks:
        b_list.append({
            "assignment_id": str(ba.assignment_id),
            "title": title,
            "completion_rate": ba.completion_rate
        })
        
    d = {c.name: getattr(ca, c.name) for c in ca.__table__.columns}
    d["class_id"] = str(d["class_id"])
    d["class_name"] = class_name
    d["risk_distribution"] = dist
    d["bottleneck_assignments"] = b_list
    return d

@router.get("/classes/{class_id}/students")
def get_class_students_analytics(class_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    if u.role == "MENTOR":
        verify_mentor_class_access(class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(class_id, u, db)
        
    query = text("""
        SELECT u.id, u.full_name, u.registration_id, sa.risk_level, sa.completion_rate, 
               sa.total_submitted, sa.total_assigned, sa.total_missed, sa.total_late, 
               sa.current_streak, sa.consecutive_misses
        FROM class_memberships cm
        JOIN users u ON u.id = cm.user_id
        LEFT JOIN student_analytics sa ON sa.student_id = u.id AND sa.class_id = cm.class_id
        WHERE cm.class_id = :class_id AND cm.member_role = 'STUDENT' AND cm.status = 'ACTIVE'
    """)
    rows = db.execute(query, {"class_id": class_id}).fetchall()
    
    res = []
    for r in rows:
        res.append({
            "student_id": str(r.id),
            "full_name": r.full_name,
            "registration_id": r.registration_id,
            "risk_level": r.risk_level or "NORMAL",
            "completion_rate": float(r.completion_rate) if r.completion_rate is not None else 0.0,
            "total_submitted": r.total_submitted or 0,
            "total_assigned": r.total_assigned or 0,
            "total_missed": r.total_missed or 0,
            "total_late": r.total_late or 0,
            "current_streak": r.current_streak or 0,
            "consecutive_misses": r.consecutive_misses or 0
        })
    return {"students": res}

@router.get("/risk/students")
def get_risk_students(class_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    if u.role == "MENTOR":
        verify_mentor_class_access(class_id, u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(class_id, u, db)
        
    query = text("""
        SELECT u.id, u.full_name, u.email, sa.risk_level, sa.completion_rate, sa.consecutive_misses
        FROM student_analytics sa
        JOIN users u ON u.id = sa.student_id
        WHERE sa.class_id = :class_id AND sa.risk_level IN ('HIGH', 'MEDIUM', 'LOW', 'RECOVERING')
        ORDER BY 
            CASE sa.risk_level 
                WHEN 'HIGH' THEN 1 
                WHEN 'MEDIUM' THEN 2 
                WHEN 'LOW' THEN 3 
                WHEN 'RECOVERING' THEN 4
            END
    """)
    rows = db.execute(query, {"class_id": class_id}).fetchall()
    
    res = []
    for r in rows:
        res.append({
            "student_id": str(r.id),
            "full_name": r.full_name,
            "email": r.email,
            "risk_level": r.risk_level,
            "completion_rate": float(r.completion_rate),
            "consecutive_misses": r.consecutive_misses
        })
    return {"at_risk_students": res}

@router.get("/admin/overview", response_model=AdminOverviewResponse)
def get_admin_overview(db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN"]))):
    total_classes = db.query(Class).filter_by(admin_id=u.id).count()
    
    total_mentors = db.query(ClassMembership).join(
        Class, Class.id == ClassMembership.class_id
    ).filter(
        Class.admin_id == u.id,
        ClassMembership.member_role == 'MENTOR',
        ClassMembership.status == 'ACTIVE'
    ).count()
    
    total_students = db.query(ClassMembership).join(
        Class, Class.id == ClassMembership.class_id
    ).filter(
        Class.admin_id == u.id,
        ClassMembership.member_role == 'STUDENT',
        ClassMembership.status == 'ACTIVE'
    ).count()
    
    total_assignments = db.query(Assignment).join(
        Class, Class.id == Assignment.class_id
    ).filter(Class.admin_id == u.id).count()
    
    query = text("""
        SELECT c.id as class_id, c.class_name, c.status, u_mentor.full_name as primary_mentor_name,
               ca.avg_completion, ca.avg_miss_rate, ca.avg_late_rate, ca.high_risk_count, ca.total_students as student_count
        FROM classes c
        LEFT JOIN class_memberships cm ON cm.class_id = c.id AND cm.member_role = 'MENTOR' AND cm.is_primary_mentor = true AND cm.status = 'ACTIVE'
        LEFT JOIN users u_mentor ON u_mentor.id = cm.user_id
        LEFT JOIN class_analytics ca ON ca.class_id = c.id
        WHERE c.admin_id = :admin_id
        ORDER BY c.created_at DESC
    """)
    rows = db.execute(query, {"admin_id": str(u.id)}).fetchall()
    
    classes = []
    for r in rows:
        classes.append({
            "class_id": str(r.class_id),
            "class_name": r.class_name,
            "status": r.status,
            "primary_mentor_name": r.primary_mentor_name,
            "avg_completion": float(r.avg_completion) if r.avg_completion is not None else 0.0,
            "avg_miss_rate": float(r.avg_miss_rate) if r.avg_miss_rate is not None else 0.0,
            "avg_late_rate": float(r.avg_late_rate) if r.avg_late_rate is not None else 0.0,
            "high_risk_count": r.high_risk_count or 0,
            "student_count": r.student_count or 0
        })
        
    return {
        "total_classes": total_classes,
        "total_mentors": total_mentors,
        "total_students": total_students,
        "total_assignments": total_assignments,
        "classes": classes
    }

@router.get("/assignments/{assignment_id}")
def get_assignment_analytics(assignment_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    # Verify assignment exists
    a = db.query(Assignment).filter_by(id=assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")
        
    if u.role == "MENTOR":
        verify_mentor_class_access(str(a.class_id), u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(str(a.class_id), u, db)
        
    aa = db.query(AssignmentAnalytics).filter_by(assignment_id=assignment_id).first()
    if not aa:
        # Not closed yet, return empty state
        return {
            "assignment_id": assignment_id,
            "title": a.title,
            "total_targets": 0,
            "submitted_count": 0,
            "missed_count": 0,
            "late_count": 0,
            "completion_rate": 0.0,
            "is_bottleneck": False
        }
        
    return {
        "assignment_id": str(aa.assignment_id),
        "title": a.title,
        "total_targets": aa.total_targets,
        "submitted_count": aa.submitted_count,
        "missed_count": aa.missed_count,
        "late_count": aa.late_count,
        "completion_rate": float(aa.completion_rate),
        "is_bottleneck": aa.is_bottleneck
    }
