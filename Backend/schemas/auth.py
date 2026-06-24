from pydantic import BaseModel

class AdminSignupRequest(BaseModel):
    full_name: str
    email: str
    password: str

class OtpVerifyRequest(BaseModel):
    email: str
    otp: str

class LoginRequest(BaseModel):
    email: str
    password: str
    registration_id: str
    fcm_token: str

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

class UserOut(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    class_id: str | None
    class_name: str | None
    registration_id: str | None

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut

class MeResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    registration_id: str | None
    class_id: str | None
    class_name: str | None
    status: str
