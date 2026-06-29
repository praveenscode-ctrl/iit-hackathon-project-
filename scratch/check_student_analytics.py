import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Backend")))

from database import SessionLocal
from models.user import User
from models.class_ import Class, ClassMembership
from models.assignment import Assignment
from models.analytics import StudentAnalytics

db = SessionLocal()

class_c = db.query(Class).filter(Class.class_name == "Class C").first()
if class_c:
    print(f"Class C ID: {class_c.id}")
    
    print("\n--- Assignments for Class C ---")
    assignments = db.query(Assignment).filter(Assignment.class_id == class_c.id).all()
    for a in assignments:
        print(f"ID: {a.id} | Title: {a.title} | Status: {a.status} | Created By: {a.created_by}")
        
    print("\n--- Syed Student Analytics Row ---")
    syed = db.query(User).filter(User.email == "themizandmorison2000@gmail.com").first()
    if syed:
        print(f"Syed ID: {syed.id}")
        sa = db.query(StudentAnalytics).filter_by(student_id=syed.id).first()
        if sa:
            print(f"total_assigned: {sa.total_assigned}")
            print(f"total_submitted: {sa.total_submitted}")
            print(f"total_missed: {sa.total_missed}")
            print(f"total_late: {sa.total_late}")
            print(f"risk_level: {sa.risk_level}")
        else:
            print("No StudentAnalytics row for Syed!")
    else:
        print("Syed not found!")
else:
    print("Class C not found!")

db.close()
