import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Backend")))

from database import SessionLocal
from models.user import User
from models.class_ import Class
from services.analytics_service import recompute_student_analytics

db = SessionLocal()

class_c = db.query(Class).filter(Class.class_name == "Class C").first()
syed = db.query(User).filter(User.email == "themizandmorison2000@gmail.com").first()

if class_c and syed:
    print(f"Running recompute_student_analytics for Syed ID: {syed.id}, Class C ID: {class_c.id}")
    recompute_student_analytics(str(syed.id), str(class_c.id), db)
    
    # Reload and check
    from models.analytics import StudentAnalytics
    db.expire_all()
    sa = db.query(StudentAnalytics).filter_by(student_id=syed.id).first()
    print("After recomputing:")
    print(f"total_assigned: {sa.total_assigned}")
    print(f"total_submitted: {sa.total_submitted}")
    print(f"total_missed: {sa.total_missed}")
    print(f"total_late: {sa.total_late}")
    print(f"risk_level: {sa.risk_level}")
else:
    print("Class C or Syed not found!")

db.close()
