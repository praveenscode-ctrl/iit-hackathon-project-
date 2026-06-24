from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.class_ import ClassMembership, Class
from utils.security import decode_token
from uuid import UUID

def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter_by(id=payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(roles: list):
    def check(u: User = Depends(get_current_user)):
        if u.role not in roles:
            raise HTTPException(status_code=403, detail="Not authorized")
        return u
    return check

def verify_mentor_class_access(class_id: UUID, u: User, db: Session):
    m = db.query(ClassMembership).filter(
        ClassMembership.user_id == u.id,
        ClassMembership.class_id == class_id,
        ClassMembership.member_role == 'MENTOR',
        ClassMembership.status == 'ACTIVE'
    ).first()
    if not m:
        raise HTTPException(status_code=403, detail="Not authorized for this class")
    return m

def verify_admin_class_access(class_id: UUID, u: User, db: Session):
    cls = db.query(Class).filter(Class.id == class_id, Class.admin_id == u.id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found or not yours")
    return cls
