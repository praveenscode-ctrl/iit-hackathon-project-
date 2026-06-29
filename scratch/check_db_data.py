import sys
import os

# Add Backend folder to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Backend")))

from database import SessionLocal
from models.user import User
from models.class_ import Class, ClassMembership

db = SessionLocal()

print("--- Class C Info ---")
class_c = db.query(Class).filter(Class.class_name == "Class C").first()
if not class_c:
    print("Class C not found in database!")
else:
    print(f"Class C ID: {class_c.id}")
    
    # Get members
    members = db.query(ClassMembership).filter(ClassMembership.class_id == class_c.id).all()
    print(f"Total members: {len(members)}")
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        if u:
            print(f"Role: {u.role} | Name: {u.full_name} | Email: {u.email} | Registration ID: {u.registration_id} | Membership Status: {m.status}")

db.close()
