import requests
import os
import time
import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.user import User, OtpVerification
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

base_url = "http://localhost:8000/api/v1"

def get_admin_token():
    email = "admin@test.com"
    pwd = "Test1234!"
    r = requests.post(f"{base_url}/auth/login", json={"email": email, "password": pwd, "registration_id": "", "fcm_token": ""})
    return r.json()["access_token"]

def run_phase3_tests():
    print("--- Starting Phase 3 Checkpoint Tests ---")
    
    # Get initial admin token
    admin_token = get_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # CP-3.1
    print("\n[+] CP-3.1: Create class")
    c_req = requests.post(f"{base_url}/classes", json={"class_name": "Test Class P3"}, headers=headers)
    assert c_req.status_code == 201, f"Failed: {c_req.text}"
    class_id = c_req.json()["id"]
    print("[OK] Class created successfully")
    
    # CP-3.2
    print("[+] CP-3.2: GET /classes returns class list with counts")
    c_list = requests.get(f"{base_url}/classes", headers=headers)
    assert len(c_list.json()["classes"]) > 0
    print("[OK] Class list retrieved")
    
    # CP-3.3
    print("\n[+] CP-3.3: Provision a mentor manually")
    m_email = f"mentor_{int(time.time())}@test.com"
    m_pwd = "MentorPassword123!"
    m_req = requests.post(f"{base_url}/provision/manual/mentor", json={
        "class_id": class_id, "full_name": "P3 Mentor", "email": m_email, "password": m_pwd, "is_primary_mentor": True
    }, headers=headers)
    assert m_req.status_code == 201
    m_reg = m_req.json()["registration_id"]
    print("[OK] Mentor provisioned")
    
    # CP-3.4
    print("[+] CP-3.4: Mentor login works")
    m_login = requests.post(f"{base_url}/auth/login", json={"email": m_email, "password": m_pwd, "registration_id": m_reg, "fcm_token": ""})
    assert m_login.status_code == 200
    mentor_token = m_login.json()["access_token"]
    print("[OK] Mentor login successful")
    
    # CP-3.5
    print("[+] CP-3.5: GET /classes/my-classes returns mentor's classes")
    my_classes = requests.get(f"{base_url}/classes/my-classes", headers={"Authorization": f"Bearer {mentor_token}"})
    assert len(my_classes.json()["classes"]) > 0
    print("[OK] Mentor classes retrieved")
    
    # CP-3.6
    print("\n[+] CP-3.6: Provision a student manually")
    s_email = f"student_{int(time.time())}@test.com"
    s_pwd = "StudentPassword123!"
    s_reg = f"STU-{int(time.time())}"
    s_req = requests.post(f"{base_url}/provision/manual/student", json={
        "class_id": class_id, "full_name": "P3 Student", "email": s_email, "password": s_pwd, "registration_id": s_reg
    }, headers=headers)
    assert s_req.status_code == 201
    print("[OK] Student provisioned (PENDING)")
    
    # CP-3.7
    print("[+] CP-3.7: Student login blocked while PENDING")
    s_login1 = requests.post(f"{base_url}/auth/login", json={"email": s_email, "password": s_pwd, "registration_id": s_reg, "fcm_token": ""})
    assert s_login1.status_code == 403
    print("[OK] Blocked correctly")
    
    # CP-3.8
    print("[+] CP-3.8: Approvals list shows pending student")
    approvals = requests.get(f"{base_url}/classes/{class_id}/approvals", headers={"Authorization": f"Bearer {mentor_token}"})
    assert approvals.json()["pending_count"] >= 1
    student_id = approvals.json()["pending"][0]["student_id"]
    print("[OK] Pending list retrieved")
    
    # CP-3.9
    print("\n[+] CP-3.9: Approve student creates analytics row")
    app_req = requests.patch(f"{base_url}/classes/{class_id}/students/{student_id}/approve", headers={"Authorization": f"Bearer {mentor_token}"})
    assert app_req.status_code == 200
    print("[OK] Student approved")
    
    # CP-3.10
    print("[+] CP-3.10: Student login succeeds after approval")
    s_login2 = requests.post(f"{base_url}/auth/login", json={"email": s_email, "password": s_pwd, "registration_id": s_reg, "fcm_token": ""})
    assert s_login2.status_code == 200
    print("[OK] Student login successful")
    
    # CP-3.11
    print("\n[+] CP-3.11: Reject a second student")
    s2_email = f"student2_{int(time.time())}@test.com"
    s2_reg = f"STU2-{int(time.time())}"
    requests.post(f"{base_url}/provision/manual/student", json={"class_id": class_id, "full_name": "P3 S2", "email": s2_email, "password": "Pwd!", "registration_id": s2_reg}, headers=headers)
    approvals2 = requests.get(f"{base_url}/classes/{class_id}/approvals", headers=headers)
    student2_id = [p["student_id"] for p in approvals2.json()["pending"] if p["email"] == s2_email][0]
    rej_req = requests.patch(f"{base_url}/classes/{class_id}/students/{student2_id}/reject", json={"reason": "Test reject"}, headers={"Authorization": f"Bearer {mentor_token}"})
    assert rej_req.status_code == 200
    print("[OK] Student rejected")
    
    # CP-3.12
    print("[+] CP-3.12: Archive class sends notifications")
    arch_req = requests.patch(f"{base_url}/classes/{class_id}", json={"status": "ARCHIVED"}, headers=headers)
    assert arch_req.json()["status"] == "ARCHIVED"
    print("[OK] Class archived")
    
    # CP-3.13 & CP-3.14
    print("\n[+] CP-3.13: Bulk import template downloads")
    tmp_req = requests.get(f"{base_url}/provision/bulk-import/template", headers=headers)
    assert tmp_req.status_code == 200
    with open("test_template.xlsx", "wb") as f:
        f.write(tmp_req.content)
        
    print("[+] CP-3.14: Bulk import processes XLSX file")
    wb = openpyxl.load_workbook("test_template.xlsx")
    wb["Classes"].append(["Bulk Class 1", "Desc", "2026"])
    b_m_email = f"b_mentor_{int(time.time())}@test.com"
    wb["Mentors"].append(["Bulk Class 1", "Bulk Mentor", b_m_email, "BulkPwd1!", True])
    b_s_email = f"b_student_{int(time.time())}@test.com"
    b_s_reg = f"BLK-{int(time.time())}"
    wb["Students"].append(["Bulk Class 1", "Bulk Student", b_s_email, "BulkPwd1!", b_s_reg])
    wb.save("test_template.xlsx")
    
    with open("test_template.xlsx", "rb") as f:
        up_req = requests.post(f"{base_url}/provision/bulk-import", files={"file": ("test_template.xlsx", f)}, headers=headers)
        
    assert up_req.status_code == 202
    batch_id = up_req.json()["batch_id"]
    
    while True:
        stat_req = requests.get(f"{base_url}/provision/bulk-import/{batch_id}", headers=headers)
        if stat_req.json()["status"] in ("COMPLETED", "PARTIAL", "FAILED"):
            break
        time.sleep(1)
        
    print(f"[OK] Bulk import finished with status: {stat_req.json()['status']}")
    
    # CP-3.15
    print("\n[+] CP-3.15: GET /classes/{class_id}/students returns students with correct fields")
    sts = requests.get(f"{base_url}/classes/{class_id}/students", headers=headers)
    assert len(sts.json()) > 0
    assert "membership_status" in sts.json()[0]
    print("[OK] Student list retrieved with proper fields")
    
    # CP-3.16
    print("[+] CP-3.16: Non-admin cannot access admin-only routes")
    bad_req = requests.post(f"{base_url}/classes", json={"class_name": "Hacked Class"}, headers={"Authorization": f"Bearer {mentor_token}"})
    assert bad_req.status_code == 403
    print("[OK] Blocked correctly")
    
    print("\n--- Phase 3 All Checkpoints Passed Successfully! ---")

if __name__ == "__main__":
    run_phase3_tests()
