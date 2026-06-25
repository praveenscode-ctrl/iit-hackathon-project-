from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from schemas.ai_query import AiQueryRequest, AiQueryResponse
from utils.dependencies import require_role, verify_mentor_class_access, verify_admin_class_access
from services.ai_service import process_ai_query

router = APIRouter()

@router.post("/query", response_model=AiQueryResponse)
async def query_ai(req: AiQueryRequest, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    if req.class_id:
        if u.role == "MENTOR":
            verify_mentor_class_access(req.class_id, u, db)
        elif u.role == "ADMIN":
            verify_admin_class_access(req.class_id, u, db)
            
    result = await process_ai_query(req.class_id, req.query_text, str(u.id), db)
    return result
