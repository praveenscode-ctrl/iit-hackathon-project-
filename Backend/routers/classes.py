from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models.user import User
from models.class_ import Class, ClassMembership
from models.analytics import ClassAnalytics, StudentAnalytics
from models.notification import Notification
from models.assignment import Assignment
from schemas.class_ import CreateClassRequest, PatchClassRequest, RejectStudentRequest, AddCoMentorRequest
from utils.dependencies import get_current_user, require_role, verify_admin_class_access, verify_mentor_class_access
from services.fcm_service import send_single_fcm
from services.email_service import send_invite_email
from utils.id_generator import make_mentor_reg_id
from utils.security import hash_password
import secrets
from datetime import datetime

router = APIRouter()

@router.post("", status_code=201)
def create_class(req: CreateClassRequest, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN"]))):
    c = Class(
        admin_id=u.id,
        class_name=req.class_name,
        description=req.description,
        academic_year=req.academic_year,
        status="ACTIVE"
    )
    db.add(c)
    db.flush()
    ca = ClassAnalytics(class_id=c.id)
    db.add(ca)
    db.commit()
    return {
        "id": str(c.id), "class_name": c.class_name, "description": c.description, 
        "academic_year": c.academic_year, "status": c.status, "created_at": c.created_at
    }

@router.get("")
def get_classes(db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN"]))):
    classes = db.query(Class).filter(Class.admin_id == u.id).all()
    res = []
    for c in classes:
        sc = db.query(func.count(ClassMembership.id)).filter(ClassMembership.class_id == c.id, ClassMembership.member_role == 'STUDENT', ClassMembership.status == 'ACTIVE').scalar()
        mc = db.query(func.count(ClassMembership.id)).filter(ClassMembership.class_id == c.id, ClassMembership.member_role == 'MENTOR', ClassMembership.status == 'ACTIVE').scalar()
        res.append({
            "id": str(c.id),
            "class_name": c.class_name,
            "description": c.description,
            "academic_year": c.academic_year,
            "status": c.status,
            "student_count": sc,
            "mentor_count": mc,
            "created_at": c.created_at.isoformat() if c.created_at else None
        })
    return {"classes": res}

@router.get("/my-classes")
def my_classes(db: Session = Depends(get_db), u: User = Depends(require_role(["MENTOR"]))):
    memberships = db.query(ClassMembership, Class).join(Class, ClassMembership.class_id == Class.id).filter(
        ClassMembership.user_id == u.id,
        ClassMembership.member_role == 'MENTOR',
        ClassMembership.status == 'ACTIVE'
    ).all()
    res = []
    for m, c in memberships:
        sc = db.query(func.count(ClassMembership.id)).filter(
            ClassMembership.class_id == c.id, 
            ClassMembership.member_role == 'STUDENT', 
            ClassMembership.status == 'ACTIVE'
        ).scalar()
        res.append({
            "id": str(c.id),
            "class_name": c.class_name,
            "status": c.status,
            "is_primary_mentor": m.is_primary_mentor,
            "student_count": sc
        })
    return {"classes": res}


@router.get("/{class_id}")
def get_class(class_id: str, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    if u.role == "ADMIN":
        c = verify_admin_class_access(class_id, u, db)
    elif u.role == "MENTOR":
        verify_mentor_class_access(class_id, u, db)
        c = db.query(Class).filter(Class.id == class_id).first()
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    sc = db.query(func.count(ClassMembership.id)).filter(ClassMembership.class_id == class_id, ClassMembership.member_role == 'STUDENT', ClassMembership.status == 'ACTIVE').scalar()
    ac = db.query(func.count(Assignment.id)).filter(Assignment.class_id == class_id).scalar()
    
    mentors = db.query(ClassMembership, User).join(User, ClassMembership.user_id == User.id).filter(
        ClassMembership.class_id == class_id,
        ClassMembership.member_role == 'MENTOR',
        ClassMembership.status == 'ACTIVE'
    ).all()
    
    pm = None
    cms = []
    for m, usr in mentors:
        o = {"id": str(usr.id), "full_name": usr.full_name, "email": usr.email}
        if m.is_primary_mentor:
            pm = o
        else:
            cms.append(o)
            
    return {
        "id": str(c.id), "class_name": c.class_name, "description": c.description,
        "academic_year": c.academic_year, "status": c.status, "student_count": sc,
        "assignment_count": ac, "primary_mentor": pm, "co_mentors": cms
    }

@router.patch("/{class_id}")
def patch_class(class_id: str, req: PatchClassRequest, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN"]))):
    c = verify_admin_class_access(class_id, u, db)
    if req.class_name is not None:
        c.class_name = req.class_name
    if req.description is not None:
        c.description = req.description
    if req.status is not None:
        c.status = req.status
        if req.status == "ARCHIVED":
            mems = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.status == 'ACTIVE').all()
            for m in mems:
                db.add(Notification(user_id=m.user_id, notification_type='CLASS_ARCHIVED', title='Class Archived', body=f'{c.class_name} has been archived.'))
    db.commit()
    return get_class(class_id, db, u)

@router.get("/{class_id}/students")
def get_students(class_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    if u.role == "ADMIN":
        verify_admin_class_access(class_id, u, db)
    else:
        verify_mentor_class_access(class_id, u, db)
        
    data = db.query(ClassMembership, User, StudentAnalytics).join(
        User, ClassMembership.user_id == User.id
    ).outerjoin(
        StudentAnalytics, (StudentAnalytics.student_id == User.id) & (StudentAnalytics.class_id == class_id)
    ).filter(
        ClassMembership.class_id == class_id,
        ClassMembership.member_role == 'STUDENT'
    ).all()
    
    res = []
    for m, usr, sa in data:
        res.append({
            "id": str(usr.id), "full_name": usr.full_name, "email": usr.email, "registration_id": usr.registration_id,
            "membership_status": m.status, "risk_level": sa.risk_level if sa else "NORMAL",
            "completion_rate": sa.completion_rate if sa else 0.0, "joined_via": m.joined_via, "joined_at": m.created_at
        })
    return {"students": res}

@router.get("/{class_id}/approvals")
def get_approvals(class_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    if u.role == "ADMIN":
        verify_admin_class_access(class_id, u, db)
    else:
        verify_mentor_class_access(class_id, u, db)
        
    data = db.query(ClassMembership, User).join(User, ClassMembership.user_id == User.id).filter(
        ClassMembership.class_id == class_id,
        ClassMembership.member_role == 'STUDENT',
        ClassMembership.status == 'PENDING'
    ).all()
    
    res = []
    for m, usr in data:
        res.append({
            "student_id": str(usr.id), "full_name": usr.full_name, "email": usr.email,
            "registration_id": usr.registration_id, "requested_at": m.created_at, "joined_via": m.joined_via
        })
    return {"pending_count": len(res), "pending": res}

@router.patch("/{class_id}/students/{student_id}/approve")
def approve_student(class_id: str, student_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    if u.role == "ADMIN":
        c = verify_admin_class_access(class_id, u, db)
    else:
        verify_mentor_class_access(class_id, u, db)
        c = db.query(Class).filter(Class.id == class_id).first()
        
    m = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.user_id == student_id, ClassMembership.member_role == 'STUDENT').first()
    if not m:
        raise HTTPException(status_code=404, detail="Student not found")
        
    m.status = 'ACTIVE'
    m.rejection_reason = None
    m.updated_at = datetime.utcnow()
    
    sa = db.query(StudentAnalytics).filter(StudentAnalytics.student_id == student_id, StudentAnalytics.class_id == class_id).first()
    if not sa:
        sa = StudentAnalytics(student_id=student_id, class_id=class_id)
        db.add(sa)
        db.flush()
        
    from services.analytics_service import recompute_student_analytics
    recompute_student_analytics(student_id, class_id, db)
        
    db.add(Notification(user_id=student_id, notification_type='STUDENT_APPROVED', title='Access Granted', body=f'You can now log in to {c.class_name}'))
    
    usr = db.query(User).filter(User.id == student_id).first()
    if usr.fcm_token:
        send_single_fcm(usr.fcm_token, "Access Granted", f"You can now log in to {c.class_name}")
        
    db.commit()
    return {"message": "Student approved", "student_id": student_id}

@router.patch("/{class_id}/students/{student_id}/reject")
def reject_student(class_id: str, student_id: str, req: RejectStudentRequest, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    if u.role == "ADMIN":
        verify_admin_class_access(class_id, u, db)
    else:
        verify_mentor_class_access(class_id, u, db)
        
    m = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.user_id == student_id, ClassMembership.member_role == 'STUDENT').first()
    if not m:
        raise HTTPException(status_code=404, detail="Student not found")
        
    m.status = 'REJECTED'
    m.rejection_reason = req.reason
    
    db.add(Notification(user_id=student_id, notification_type='STUDENT_REJECTED', title='Access Denied', body=req.reason))
    
    usr = db.query(User).filter(User.id == student_id).first()
    if usr.fcm_token:
        send_single_fcm(usr.fcm_token, "Access Denied", req.reason)
        
    db.commit()
    return {"message": "Student rejected"}

@router.post("/{class_id}/co-mentors", status_code=201)
def add_comentor(class_id: str, req: AddCoMentorRequest, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN"]))):
    c = verify_admin_class_access(class_id, u, db)
    
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=409, detail="Email exists")
        
    pwd = secrets.token_urlsafe(8)
    reg = make_mentor_reg_id()
    
    nu = User(role='MENTOR', status='ACTIVE', full_name=req.full_name, email=req.email, password_hash=hash_password(pwd), registration_id=reg)
    db.add(nu)
    db.flush()
    
    db.add(ClassMembership(class_id=class_id, user_id=nu.id, member_role='MENTOR', is_primary_mentor=False, status='ACTIVE', joined_via='MANUAL'))
    db.add(Notification(user_id=nu.id, notification_type='CO_MENTOR_ADDED', title='Added as Co-Mentor', body=f'You were added to {c.class_name}'))
    db.commit()
    
    send_invite_email(req.email, req.full_name, pwd, reg, c.class_name)
    return {"id": str(nu.id), "full_name": nu.full_name, "email": nu.email, "registration_id": nu.registration_id, "message": "Invitation email sent"}
