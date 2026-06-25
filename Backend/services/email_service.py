import smtplib
from email.mime.text import MIMEText
import os
from fastapi import HTTPException

def send_otp_email(to: str, code: str):
    addr = os.getenv("GMAIL_ADDRESS")
    pwd = os.getenv("GMAIL_APP_PASSWORD")
    msg = MIMEText(f"Your OTP to verify your AssignHub admin account: {code}\nThis OTP is valid for 10 minutes.\nDo not share this OTP with anyone.")
    msg['Subject'] = "Your AssignHub OTP"
    msg['From'] = addr
    msg['To'] = to
    try:
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(addr, pwd)
        s.send_message(msg)
        s.quit()
    except Exception as e:
        print(f"otp email failed: {e}")
        print(f"\n==================================================")
        print(f"⚠️  [SMTP BYPASSED] OTP FOR {to} IS: {code}")
        print(f"==================================================\n")
        # Log and bypass to allow local signup & testing to succeed

def send_invite_email(to: str, name: str, pwd: str, reg_id: str, cls_name: str):
    frm = os.getenv("SENDER_EMAIL")
    frm_name = os.getenv("SENDER_NAME", "AssignHub")
    host = os.getenv("BREVO_SMTP_HOST")
    port = int(os.getenv("BREVO_SMTP_PORT", "587"))
    user = os.getenv("BREVO_SMTP_USER")
    key = os.getenv("BREVO_SMTP_KEY")
    body = (
        f"Hello {name},\n\n"
        f"You have been invited to join {cls_name} on AssignHub.\n\n"
        f"Email: {to}\n"
        f"Password: {pwd}\n"
        f"Registration ID: {reg_id}\n\n"
        f"Log in and change your password.\n\n"
        f"- AssignHub Team"
    )
    msg = MIMEText(body)
    msg['Subject'] = "Welcome to AssignHub — Your Login Details"
    msg['From'] = f"{frm_name} <{frm}>"
    msg['To'] = to
    try:
        s = smtplib.SMTP(host, port)
        s.starttls()
        s.login(user, key)
        s.send_message(msg)
        s.quit()
    except Exception as e:
        print(f"invite email failed: {e}")
        print(f"\n==================================================")
        print(f"⚠️  [SMTP BYPASSED] INVITATION DETAILS:")
        print(f"Name: {name} | Email: {to}")
        print(f"Password: {pwd} | Registration ID: {reg_id}")
        print(f"Class: {cls_name}")
        print(f"==================================================\n")
        # Log and bypass to allow manual provisioning to succeed
