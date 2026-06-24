from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.user import User, OtpVerification, AdminProfile, RefreshToken
from models.class_ import ClassMembership, Class
from schemas.auth import AdminSignupRequest, OtpVerifyRequest, LoginRequest, RefreshRequest, LogoutRequest, LoginResponse, MeResponse
from utils.security import hash_password, verify_password, make_otp, make_access_token, hash_refresh_token, verify_refresh_token
from services.email_service import send_otp_email
from utils.dependencies import get_current_user
from datetime import datetime, timedelta
import uuid

router = APIRouter()

@router.post("/admin/signup", status_code=201)
def admin_signup(req: AdminSignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    
    u = User(
        role="ADMIN",
        full_name=req.full_name,
        email=req.email,
        password_hash=hash_password(req.password),
        status="PENDING_OTP"
    )
    db.add(u)
    
    otp = make_otp()
    ov = OtpVerification(
        email=req.email,
        otp_code=otp,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(ov)
    db.commit()
    
    send_otp_email(req.email, otp)
    return {"message": "OTP sent to your email"}

@router.post("/admin/verify-otp")
def verify_otp(req: OtpVerifyRequest, db: Session = Depends(get_db)):
    ov = db.query(OtpVerification).filter(
        OtpVerification.email == req.email, 
        OtpVerification.used == False
    ).order_by(OtpVerification.created_at.desc()).first()
    
    if not ov:
        raise HTTPException(status_code=400, detail="No pending OTP")
    
    # Needs timezone awareness if expires_at is TIMESTAMPTZ, but utcnow is naive.
    # In python 3.11+, datetime.now(timezone.utc) is better, but doing simple naive comparison if expires_at is naive.
    # Let's use utcnow and ensure expires_at is compared correctly.
    if ov.expires_at.replace(tzinfo=None) < datetime.utcnow():
        raise HTTPException(status_code=410, detail="OTP expired")
        
    if ov.otp_code != req.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    ov.used = True
    u = db.query(User).filter(User.email == req.email).first()
    u.status = "ACTIVE"
    
    ap = AdminProfile(user_id=u.id)
    db.add(ap)
    
    acc_tok = make_access_token(str(u.id), "ADMIN", None)
    ref_tok = str(uuid.uuid4())
    
    rt = RefreshToken(
        user_id=u.id,
        token_hash=hash_refresh_token(ref_tok),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(rt)
    db.commit()
    
    return {
        "access_token": acc_tok,
        "refresh_token": ref_tok,
        "user": {
            "id": str(u.id),
            "full_name": u.full_name,
            "role": "ADMIN",
            "email": u.email,
            "class_id": None,
            "class_name": None,
            "registration_id": None
        }
    }

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == req.email).first()
    if not u or not verify_password(req.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if u.role in ("MENTOR", "STUDENT") and u.registration_id != req.registration_id:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if u.status == "PENDING_OTP":
        raise HTTPException(status_code=403, detail="Account not verified")
    if u.status == "BLOCKED":
        raise HTTPException(status_code=403, detail="Account blocked")
    if u.status == "INACTIVE":
        raise HTTPException(status_code=403, detail="Account inactive")
        
    m = None
    c_name = None
    if u.role == "STUDENT":
        m = db.query(ClassMembership).filter(ClassMembership.user_id == u.id, ClassMembership.status == "ACTIVE").first()
        if not m:
            raise HTTPException(status_code=403, detail="Account pending approval. Please wait for your mentor to approve your access.")
    elif u.role == "MENTOR":
        m = db.query(ClassMembership).filter(ClassMembership.user_id == u.id, ClassMembership.status == "ACTIVE").first()
        if not m:
            raise HTTPException(status_code=403, detail="No active class assignment found")
            
    if req.fcm_token:
        u.fcm_token = req.fcm_token
        
    cid = str(m.class_id) if m else None
    
    if cid:
        cls = db.query(Class).filter(Class.id == cid).first()
        c_name = cls.class_name if cls else None
        
    acc_tok = make_access_token(str(u.id), u.role, cid)
    ref_tok = str(uuid.uuid4())
    
    rt = RefreshToken(
        user_id=u.id,
        token_hash=hash_refresh_token(ref_tok),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(rt)
    db.commit()
    
    return {
        "access_token": acc_tok,
        "refresh_token": ref_tok,
        "user": {
            "id": str(u.id),
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "class_id": cid,
            "class_name": c_name,
            "registration_id": u.registration_id
        }
    }

@router.post("/refresh")
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    # Very simple implementation, avoiding complex queries
    rt_records = db.query(RefreshToken).filter(RefreshToken.revoked == False).all()
    
    valid_rt = None
    for r in rt_records:
        if verify_refresh_token(req.refresh_token, r.token_hash) and r.expires_at.replace(tzinfo=None) > datetime.utcnow():
            valid_rt = r
            break
            
    if not valid_rt:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    u = db.query(User).filter(User.id == valid_rt.user_id).first()
    
    m = db.query(ClassMembership).filter(ClassMembership.user_id == u.id, ClassMembership.status == "ACTIVE").first()
    cid = str(m.class_id) if m else None
    
    acc_tok = make_access_token(str(u.id), u.role, cid)
    return {"access_token": acc_tok}

@router.post("/logout")
def logout(req: LogoutRequest, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    rt_records = db.query(RefreshToken).filter(RefreshToken.user_id == u.id, RefreshToken.revoked == False).all()
    
    for r in rt_records:
        if verify_refresh_token(req.refresh_token, r.token_hash):
            r.revoked = True
            break
            
    db.commit()
    return {"message": "Logged out"}

@router.get("/me", response_model=MeResponse)
def me(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    m = db.query(ClassMembership).filter(ClassMembership.user_id == u.id, ClassMembership.status == "ACTIVE").first()
    cid = str(m.class_id) if m else None
    c_name = None
    if cid:
        cls = db.query(Class).filter(Class.id == cid).first()
        c_name = cls.class_name if cls else None
        
    return {
        "id": str(u.id),
        "full_name": u.full_name,
        "email": u.email,
        "role": u.role,
        "registration_id": u.registration_id,
        "class_id": cid,
        "class_name": c_name,
        "status": u.status
    }
