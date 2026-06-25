from pydantic import BaseModel

class CreateMentorRequest(BaseModel):
    class_id: str
    full_name: str
    email: str
    password: str
    is_primary_mentor: bool = False

class CreateStudentRequest(BaseModel):
    class_id: str
    full_name: str
    email: str
    password: str
    registration_id: str
