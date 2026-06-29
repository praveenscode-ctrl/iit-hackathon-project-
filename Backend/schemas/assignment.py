from pydantic import BaseModel

class CreateAssignmentRequest(BaseModel):
    class_id: str
    title: str
    description: str | None = None
    content_type: str
    content_url: str | None = None
    rich_text_body: str | None = None
    submission_type: str
    deadline_at: str | None = None
    auto_close: bool = False

class SubmitRequest(BaseModel):
    submission_type: str
    file_url: str | None = None
    text_answer: str | None = None
    late_reason: str | None = None

class PresignedUploadRequest(BaseModel):
    file_name: str
    file_type: str
    upload_purpose: str

class PresignedDownloadRequest(BaseModel):
    file_url: str

class ReminderRequest(BaseModel):
    assignment_id: str
    remind_at: str
