from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.assignment import Assignment
from models.export import ExportJob
from utils.dependencies import require_role, verify_mentor_class_access, verify_admin_class_access
from services.export_service import generate_export
from pydantic import BaseModel

router = APIRouter()

class ExportRequest(BaseModel):
    assignment_id: str

@router.post("/assignment-tracker", status_code=202)
def create_export(req: ExportRequest, background: BackgroundTasks, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    a = db.query(Assignment).filter_by(id=req.assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")
        
    if a.status == 'DRAFT':
        raise HTTPException(409, "Assignment must be published or closed before exporting")
        
    if u.role == "MENTOR":
        verify_mentor_class_access(str(a.class_id), u, db)
    elif u.role == "ADMIN":
        verify_admin_class_access(str(a.class_id), u, db)
        
    job = ExportJob(
        requested_by=u.id,
        assignment_id=a.id,
        export_type='ASSIGNMENT_TRACKER',
        status='PENDING'
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    background.add_task(generate_export, str(job.id), db)
    
    return {"export_job_id": str(job.id), "status": "PENDING"}

@router.get("/{export_job_id}")
def get_export_status(export_job_id: str, db: Session = Depends(get_db), u: User = Depends(require_role(["ADMIN", "MENTOR"]))):
    job = db.query(ExportJob).filter_by(id=export_job_id).first()
    if not job:
        raise HTTPException(404, "Export job not found")
        
    if str(job.requested_by) != str(u.id):
        raise HTTPException(403, "Not your export job")
        
    return {
        "export_job_id": str(job.id),
        "status": job.status,
        "file_url": job.file_url
    }
