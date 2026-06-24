from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import random
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def make_access_token(user_id: str, role: str, class_id: str | None) -> str:
    expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    to_encode = {"sub": user_id, "role": role, "class_id": class_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, os.getenv("JWT_SECRET_KEY"), algorithm=os.getenv("JWT_ALGORITHM"))
    return encoded_jwt

def decode_token(token: str) -> dict:
    return jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=[os.getenv("JWT_ALGORITHM")])

def make_otp() -> str:
    return str(random.randint(100000, 999999))

def hash_refresh_token(token: str) -> str:
    return pwd_context.hash(token)

def verify_refresh_token(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
