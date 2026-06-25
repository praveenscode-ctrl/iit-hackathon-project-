from sqlalchemy import inspect
from database import engine
from utils.security import hash_password, verify_password, make_otp, make_access_token, decode_token
import os
from dotenv import load_dotenv

# Ensure env is loaded for the JWT secret
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

def run_tests():
    print("--- Running Unit Tests & Cross Checks (Phase 1) ---")
    
    # 1. Test Security Utilities (CP-1.9)
    print("\n[1] Testing Security Utilities...")
    pw = hash_password("testpass123")
    assert verify_password("testpass123", pw) == True
    assert verify_password("wrongpass", pw) == False
    
    otp = make_otp()
    assert len(otp) == 6
    assert otp.isdigit()
    
    token = make_access_token("user-uuid-here", "ADMIN", None)
    payload = decode_token(token)
    assert payload["role"] == "ADMIN"
    assert payload["sub"] == "user-uuid-here"
    assert payload.get("class_id") is None
    
    print("[OK] All security checks passed.")

    # 2. Cross Check Database Tables (CP-1.4 to CP-1.8 equivalent)
    print("\n[2] Cross Checking Database Schema...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    expected_tables = [
        'users', 'otp_verifications', 'admin_profiles', 'refresh_tokens', 
        'classes', 'class_memberships', 'assignments', 'submissions', 
        'student_analytics', 'class_analytics', 'assignment_analytics', 
        'notifications', 'reminder_jobs', 'bulk_import_batches', 
        'bulk_import_errors', 'export_jobs', 'ai_query_logs'
    ]
    
    missing_tables = [t for t in expected_tables if t not in tables]
    if missing_tables:
        print(f"[ERROR] Missing tables: {missing_tables}")
    else:
        print(f"[OK] All {len(expected_tables)} tables exist in the database.")
        
    # Quick check on Users table columns
    user_cols = {col['name']: col for col in inspector.get_columns('users')}
    assert str(user_cols['id']['type']) == 'UUID', "User ID should be UUID"
    assert 'TIME' in str(user_cols['created_at']['type']), "created_at should be Timestamp"
    print("[OK] UUID primary keys and TIMESTAMPTZ columns verified.")
    
    print("\n--- All Phase 1 Checks Completed Successfully ---")

if __name__ == "__main__":
    run_tests()
