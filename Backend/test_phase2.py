import requests
import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.user import User, OtpVerification
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

base_url = "http://localhost:8000/api/v1/auth"

def run_integration_test():
    email = f"admin_{int(time.time())}@test.com"
    password = "SecurePassword123!"
    
    print(f"--- Starting Full E2E Admin Creation Test ---")
    print(f"[*] Generated unique test email: {email}")

    # 1. Signup
    print("\n[+] Testing POST /admin/signup...")
    r_signup = requests.post(f"{base_url}/admin/signup", json={
        "full_name": "E2E Test Admin",
        "email": email,
        "password": password
    })
    
    if r_signup.status_code == 201:
        print("[OK] Signup successful. OTP should be sent and user in DB as PENDING_OTP.")
    else:
        print(f"[-] Signup failed: {r_signup.text}")
        return

    # Check DB for User
    user = db.query(User).filter(User.email == email).first()
    print(f"[*] DB Check: User status is '{user.status}' (Expected: PENDING_OTP)")

    # 2. Get OTP from DB
    ov = db.query(OtpVerification).filter(
        OtpVerification.email == email, 
        OtpVerification.used == False
    ).order_by(OtpVerification.created_at.desc()).first()
    
    otp = ov.otp_code
    print(f"[*] Fetched OTP from DB directly: {otp}")

    # 3. Verify OTP
    print("\n[+] Testing POST /admin/verify-otp...")
    r_verify = requests.post(f"{base_url}/admin/verify-otp", json={
        "email": email,
        "otp": otp
    })
    
    if r_verify.status_code == 200:
        print("[OK] OTP verification successful! Account should now be ACTIVE.")
    else:
        print(f"[-] OTP Verify failed: {r_verify.text}")
        return

    # Check DB for User
    db.refresh(user)
    print(f"[*] DB Check: User status is '{user.status}' (Expected: ACTIVE)")

    # 4. Login
    print("\n[+] Testing POST /login...")
    r_login = requests.post(f"{base_url}/login", json={
        "email": email,
        "password": password,
        "registration_id": "",
        "fcm_token": ""
    })
    
    if r_login.status_code == 200:
        print("[OK] Login successful! Tokens generated.")
        token = r_login.json()["access_token"]
    else:
        print(f"[-] Login failed: {r_login.text}")
        return

    # 5. Check Auth (GET /me)
    print("\n[+] Testing GET /me to verify JWT Authorization Guard...")
    r_me = requests.get(f"{base_url}/me", headers={"Authorization": f"Bearer {token}"})
    if r_me.status_code == 200:
        data = r_me.json()
        print(f"[OK] Auth successful! Retrieved profile: {data['full_name']} ({data['role']})")
    else:
        print(f"[-] /me failed: {r_me.text}")

    print("\n--- E2E Test Completed Successfully! ---")

if __name__ == "__main__":
    run_integration_test()
