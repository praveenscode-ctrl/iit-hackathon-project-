from fastapi import APIRouter, Depends, HTTPException
from models.user import User
from schemas.assignment import PresignedUploadRequest, PresignedDownloadRequest
from utils.dependencies import require_role
from services import s3_service

router = APIRouter()

@router.post("/presigned-upload")
def presigned_upload(req: PresignedUploadRequest, u: User = Depends(require_role(["ADMIN", "MENTOR", "STUDENT"]))):
    return s3_service.get_presigned_upload(req.file_name, req.file_type, req.upload_purpose, str(u.id))

@router.post("/presigned-download")
def presigned_download(req: PresignedDownloadRequest, u: User = Depends(require_role(["ADMIN", "MENTOR", "STUDENT"]))):
    try:
        return s3_service.get_presigned_download(req.file_url)
    except ValueError as e:
        raise HTTPException(400, str(e))
