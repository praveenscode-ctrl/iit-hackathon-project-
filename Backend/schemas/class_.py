from pydantic import BaseModel

class CreateClassRequest(BaseModel):
    class_name: str
    description: str | None = None
    academic_year: str | None = None

class PatchClassRequest(BaseModel):
    class_name: str | None = None
    description: str | None = None
    status: str | None = None

class RejectStudentRequest(BaseModel):
    reason: str

class AddCoMentorRequest(BaseModel):
    full_name: str
    email: str
