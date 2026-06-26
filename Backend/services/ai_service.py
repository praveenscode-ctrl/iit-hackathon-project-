import os
import json
from typing import Dict, Any, Optional
import httpx
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from models.assignment import Assignment
from models.class_ import ClassMembership, Class
from models.user import User
from models.analytics import StudentAnalytics, ClassAnalytics, AssignmentAnalytics
from models.submission import Submission
from models.export import AiQueryLog

async def call_llm_api(system_prompt: str, user_message: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return '{"intent": "unknown", "params": {}}'
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, headers=headers, json=payload, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print("LLM Error:", e)
            return '{"intent": "unknown", "params": {}}'

def no_data_response(message: str = "I can answer questions about analytics, assignments, submissions, and rosters.") -> Dict:
    return {
        "type": "no_data",
        "data": [],
        "message": message
    }

def get_temporal_date_range(temporal_ref: str):
    now = datetime.now(timezone.utc)
    temporal_ref = temporal_ref.lower()
    if temporal_ref == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)
    elif temporal_ref == "yesterday":
        start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)
    elif temporal_ref in ["day before yesterday", "day_before_yesterday"]:
        start = (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)
    elif temporal_ref == "last week":
        start = (now - timedelta(days=now.weekday() + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=7)
    elif temporal_ref == "this week":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=7)
    return None, None

async def process_ai_query(class_id: Optional[str], query_text: str, user_id: str, db: Session) -> dict:
    system_prompt = """You are an intent extractor for an educational admin tool.
Extract intent and params from the user query. Return ONLY a valid JSON object.
Format: {"intent": "string", "params": {"student_name": "string", "assignment_ref": "string", "temporal_ref": "string", "sort_order": "string"}}
Valid intents: 
- who_missed_assignment
- who_submitted_assignment
- student_completion_rate
- class_summary
- risk_students
- student_profile
- general_count
- class_roster
- pending_approvals
- all_my_classes
- mentor_list
- assignment_list
- assignment_status
- assignment_analytics
- bottleneck_assignments
- late_submitters
- submission_history
- streak_leaders
- admin_overview
- class_health
- unknown

Temporal refs can be exactly: 'today', 'yesterday', 'day before yesterday', 'this week', 'last week'.
"""
    
    llm_response = await call_llm_api(system_prompt, query_text)
    
    try:
        parsed = json.loads(llm_response)
    except json.JSONDecodeError:
        parsed = {"intent": "unknown", "params": {}}
        
    intent = parsed.get("intent", "unknown")
    params = parsed.get("params", {})
    
    result = {}
    action_links = []
    
    caller = db.query(User).filter_by(id=user_id).first()
    
    if caller.role == "ADMIN":
        classes = db.query(Class).filter_by(admin_id=caller.id).all()
    else:
        classes = db.query(Class).join(ClassMembership).filter(ClassMembership.user_id == caller.id).all()
        
    class_ids = [str(c.id) for c in classes]
    class_names = {str(c.id): c.class_name for c in classes}
    
    class_scoped_intents = {"who_submitted_assignment", "who_missed_assignment", "student_completion_rate", "student_profile", "class_summary", "risk_students", "class_roster", "pending_approvals", "mentor_list", "assignment_list", "assignment_status", "assignment_analytics", "bottleneck_assignments", "late_submitters", "submission_history", "streak_leaders"}
    if intent in class_scoped_intents and not class_id and not class_ids:
        result = no_data_response("You don't have any classes created yet.")
        response_payload = {"intent": intent, "query_text": query_text, "result": result, "action_links": []}
        _log_query(db, user_id, class_id, query_text, intent, response_payload)
        return response_payload

    def get_assignment_by_ref(a_ref, t_ref):
        if class_id:
            query = db.query(Assignment).filter(Assignment.class_id == class_id)
        else:
            query = db.query(Assignment).filter(Assignment.class_id.in_(class_ids))
            
        c_names = list(class_names.values())
        if class_id:
            c_obj = db.query(Class).filter_by(id=class_id).first()
            if c_obj:
                c_names.append(c_obj.class_name)
                
        cleaned_ref = None
        if a_ref:
            ref = a_ref.lower().strip()
            # Remove class name references
            for c_name in c_names:
                c_name_lower = c_name.lower()
                for prefix in ["in class ", "for class ", "in ", "for "]:
                    pattern = f"{prefix}{c_name_lower}"
                    if pattern in ref:
                        ref = ref.replace(pattern, "")
            
            # Remove trailing class name if any left
            for c_name in c_names:
                c_name_lower = c_name.lower()
                if ref.endswith(f" {c_name_lower}"):
                    ref = ref[:-len(c_name_lower) - 1].strip()
            
            ref = ref.strip()
            if ref.endswith(" in"):
                ref = ref[:-3].strip()
            if ref.endswith(" for"):
                ref = ref[:-4].strip()
                
            generic_words = {"recent", "recent assignment", "latest", "latest assignment", "last", "last assignment", "the assignment", "assignment", "recent assignments", "assignments"}
            if ref not in generic_words:
                cleaned_ref = ref

        if cleaned_ref:
            query = query.filter(Assignment.title.ilike(f"%{cleaned_ref}%"))
            
        if t_ref:
            t_ref_lower = t_ref.lower()
            query_lower = query_text.lower()
            should_apply_temporal = False
            
            if "today" in t_ref_lower and "today" in query_lower:
                should_apply_temporal = True
            elif "yesterday" in t_ref_lower and "yesterday" in query_lower:
                should_apply_temporal = True
            elif "week" in t_ref_lower and "week" in query_lower:
                should_apply_temporal = True
                
            if should_apply_temporal:
                start, end = get_temporal_date_range(t_ref)
                if start and end:
                    query = query.filter(Assignment.deadline_at >= start, Assignment.deadline_at < end)
        return query.order_by(Assignment.created_at.desc()).first()

    if intent == "who_missed_assignment":
        assignment_ref = params.get("assignment_ref")
        temporal_ref = params.get("temporal_ref")
        assignment = get_assignment_by_ref(assignment_ref, temporal_ref)
        if not assignment:
            result = no_data_response(f"Could not find an assignment matching your query.")
        else:
            non_submitters = db.execute(text("""
                SELECT u.id, u.full_name, u.registration_id
                FROM users u
                JOIN class_memberships cm ON cm.user_id = u.id
                    AND cm.class_id = :class_id
                    AND cm.member_role = 'STUDENT'
                    AND cm.status = 'ACTIVE'
                LEFT JOIN submissions s ON s.student_id = u.id
                    AND s.assignment_id = :assignment_id
                    AND s.is_current = true
                WHERE s.id IS NULL
            """), {"class_id": str(assignment.class_id), "assignment_id": str(assignment.id)}).fetchall()
            
            result = {
                "type": "student_list",
                "data": [{"student_id": str(r.id), "full_name": r.full_name, "registration_id": r.registration_id} for r in non_submitters],
                "message": f"{len(non_submitters)} student(s) have not submitted '{assignment.title}'"
            }
            action_links = [{"label": f"View {r.full_name}", "route": f"/analytics/students/{r.id}"} for r in non_submitters[:3]]

    elif intent == "who_submitted_assignment":
        assignment_ref = params.get("assignment_ref")
        temporal_ref = params.get("temporal_ref")
        assignment = get_assignment_by_ref(assignment_ref, temporal_ref)
        if not assignment:
            result = no_data_response(f"Could not find an assignment matching your query.")
        else:
            submitters = db.execute(text("""
                SELECT u.id, u.full_name, u.registration_id, s.is_late
                FROM users u
                JOIN class_memberships cm ON cm.user_id = u.id
                    AND cm.class_id = :class_id
                    AND cm.member_role = 'STUDENT'
                    AND cm.status = 'ACTIVE'
                JOIN submissions s ON s.student_id = u.id
                    AND s.assignment_id = :assignment_id
                    AND s.is_current = true
            """), {"class_id": str(assignment.class_id), "assignment_id": str(assignment.id)}).fetchall()
            
            lines = [f"- {r.full_name} ({'Late' if r.is_late else 'On Time'})" for r in submitters]
            msg = f"{len(submitters)} student(s) have submitted '{assignment.title}':\n" + "\n".join(lines) if submitters else f"No student has submitted '{assignment.title}' yet."
            result = {
                "type": "student_list",
                "data": [{"student_id": str(r.id), "full_name": r.full_name, "registration_id": r.registration_id} for r in submitters],
                "message": msg
            }
            action_links = [{"label": f"View {r.full_name}", "route": f"/analytics/students/{r.id}"} for r in submitters[:3]]

    elif intent == "late_submitters":
        assignment_ref = params.get("assignment_ref")
        temporal_ref = params.get("temporal_ref")
        assignment = get_assignment_by_ref(assignment_ref, temporal_ref)
        if not assignment:
            result = no_data_response(f"Could not find matching assignment.")
        else:
            lates = db.execute(text("""
                SELECT u.id, u.full_name, s.submitted_at
                FROM users u
                JOIN submissions s ON s.student_id = u.id
                WHERE s.assignment_id = :assignment_id AND s.is_late = true AND s.is_current = true
            """), {"assignment_id": str(assignment.id)}).fetchall()
            result = {
                "type": "student_list",
                "data": [{"student_id": str(r.id), "full_name": r.full_name, "info": str(r.submitted_at)} for r in lates],
                "message": f"{len(lates)} student(s) submitted '{assignment.title}' late."
            }

    elif intent == "student_completion_rate":
        student_name = params.get("student_name")
        if not student_name:
            result = no_data_response("Which student? Try: 'What is Ravi's completion rate?'")
        else:
            query = db.query(User, ClassMembership.class_id).join(ClassMembership)
            if class_id:
                query = query.filter(ClassMembership.class_id == class_id)
            else:
                query = query.filter(ClassMembership.class_id.in_(class_ids))
            row = query.filter(
                ClassMembership.member_role == 'STUDENT',
                User.full_name.ilike(f"%{student_name}%")
            ).first()
            if not row:
                result = no_data_response(f"No student named '{student_name}' found.")
            else:
                student, s_class_id = row
                sa = db.query(StudentAnalytics).filter_by(student_id=student.id, class_id=s_class_id).first()
                comp_rate = float(sa.completion_rate) if sa else 0.0
                result = {
                    "type": "student_profile",
                    "data": [{"full_name": student.full_name, "completion_rate": comp_rate, "risk_level": sa.risk_level if sa else "NORMAL"}],
                    "message": f"{student.full_name}'s completion rate is {comp_rate}%"
                }
                action_links = [{"label": f"View {student.full_name}'s full profile", "route": f"/analytics/students/{student.id}"}]

    elif intent == "student_profile":
        student_name = params.get("student_name")
        if not student_name:
            result = no_data_response("Which student?")
        else:
            query = db.query(User, ClassMembership.class_id).join(ClassMembership)
            if class_id:
                query = query.filter(ClassMembership.class_id == class_id)
            else:
                query = query.filter(ClassMembership.class_id.in_(class_ids))
            row = query.filter(
                ClassMembership.member_role == 'STUDENT',
                User.full_name.ilike(f"%{student_name}%")
            ).first()
            if not row:
                result = no_data_response(f"No student named '{student_name}' found.")
            else:
                student, s_class_id = row
                sa = db.query(StudentAnalytics).filter_by(student_id=student.id, class_id=s_class_id).first()
                if not sa:
                    result = no_data_response(f"No analytics data for '{student.full_name}'.")
                else:
                    result = {
                        "type": "student_profile",
                        "data": [{
                            "full_name": student.full_name,
                            "completion_rate": float(sa.completion_rate),
                            "total_submitted": sa.total_submitted,
                            "total_assigned": sa.total_assigned,
                            "risk_level": sa.risk_level
                        }],
                        "message": f"{student.full_name} profile summary."
                    }
                    action_links = [{"label": "View full profile", "route": f"/analytics/students/{student.id}"}]

    elif intent == "class_summary":
        if class_id:
            ca = db.query(ClassAnalytics).filter_by(class_id=class_id).first()
            if not ca:
                result = no_data_response("No analytics data available yet.")
            else:
                result = {
                    "type": "class_summary",
                    "data": [{
                        "avg_completion": float(ca.avg_completion),
                        "avg_miss_rate": float(ca.avg_miss_rate),
                        "high_risk_count": ca.high_risk_count,
                        "total_students": ca.total_students
                    }],
                    "message": f"Class completion: {ca.avg_completion}% | At-risk: {ca.high_risk_count}"
                }
        else:
            ca_rows = db.query(ClassAnalytics, Class.class_name).join(Class, Class.id == ClassAnalytics.class_id).filter(
                ClassAnalytics.class_id.in_(class_ids)
            ).all()
            if not ca_rows:
                result = no_data_response("No analytics data available yet.")
            else:
                lines = [f"- {c_name}: Completion: {float(ca.avg_completion)}% | At-risk: {ca.high_risk_count}" for ca, c_name in ca_rows]
                result = {
                    "type": "class_summary",
                    "data": [],
                    "message": "Overview of all classes:\n" + "\n".join(lines)
                }

    elif intent == "risk_students":
        if class_id:
            risk_rows = db.query(StudentAnalytics, User).join(
                User, User.id == StudentAnalytics.student_id
            ).filter(
                StudentAnalytics.class_id == class_id,
                StudentAnalytics.risk_level.in_(["HIGH", "MEDIUM", "RECOVERING"])
            ).order_by(StudentAnalytics.consecutive_misses.desc()).all()
            
            result = {
                "type": "student_list",
                "data": [{"full_name": u.full_name, "info": sa.risk_level} for sa, u in risk_rows],
                "message": f"Found {len(risk_rows)} at-risk/recovering students."
            }
        else:
            risk_rows = db.query(StudentAnalytics, User, Class.class_name).join(
                User, User.id == StudentAnalytics.student_id
            ).join(Class, Class.id == StudentAnalytics.class_id).filter(
                StudentAnalytics.class_id.in_(class_ids),
                StudentAnalytics.risk_level.in_(["HIGH", "MEDIUM", "RECOVERING"])
            ).order_by(StudentAnalytics.consecutive_misses.desc()).all()
            
            lines = [f"- {u.full_name} ({c_name}): {sa.risk_level}" for sa, u, c_name in risk_rows]
            result = {
                "type": "student_list",
                "data": [{"full_name": u.full_name, "info": f"{c_name} - {sa.risk_level}"} for sa, u, c_name in risk_rows],
                "message": f"Found {len(risk_rows)} at-risk/recovering student(s):\n" + "\n".join(lines)
            }

    elif intent == "streak_leaders":
        if class_id:
            leaders = db.query(StudentAnalytics, User).join(User, User.id == StudentAnalytics.student_id).filter(
                StudentAnalytics.class_id == class_id
            ).order_by(StudentAnalytics.current_streak.desc()).limit(5).all()
            result = {
                "type": "student_list",
                "data": [{"full_name": u.full_name, "info": f"Streak: {sa.current_streak}"} for sa, u in leaders],
                "message": "Top streak leaders in the class."
            }
        else:
            leaders = db.query(StudentAnalytics, User, Class.class_name).join(
                User, User.id == StudentAnalytics.student_id
            ).join(Class, Class.id == StudentAnalytics.class_id).filter(
                StudentAnalytics.class_id.in_(class_ids)
            ).order_by(StudentAnalytics.current_streak.desc()).limit(5).all()
            result = {
                "type": "student_list",
                "data": [{"full_name": u.full_name, "info": f"{c_name} (Streak: {sa.current_streak})"} for sa, u, c_name in leaders],
                "message": "Top streak leaders across all classes."
            }

    elif intent == "class_roster":
        if class_id:
            roster = db.query(User).join(ClassMembership).filter(
                ClassMembership.class_id == class_id,
                ClassMembership.status == 'ACTIVE',
                ClassMembership.member_role == 'STUDENT'
            ).all()
            result = {
                "type": "student_list",
                "data": [{"full_name": u.full_name, "info": u.email} for u in roster],
                "message": f"Found {len(roster)} active students in this class."
            }
        else:
            members = db.query(User, ClassMembership.member_role, Class.class_name).join(
                ClassMembership, ClassMembership.user_id == User.id
            ).join(Class, Class.id == ClassMembership.class_id).filter(
                ClassMembership.class_id.in_(class_ids),
                ClassMembership.status == 'ACTIVE'
            ).all()
            
            from collections import defaultdict
            grouped_students = defaultdict(list)
            grouped_mentors = defaultdict(list)
            for u, role, c_name in members:
                if role == 'STUDENT':
                    grouped_students[c_name].append(u.full_name)
                elif role == 'MENTOR':
                    grouped_mentors[c_name].append(u.full_name)
            
            lines = []
            all_classes = db.query(Class).filter(Class.id.in_(class_ids)).all()
            lines.append(f"You have created {len(all_classes)} class(es):\n")
            for c in all_classes:
                c_name = c.class_name
                mentors_str = ", ".join(grouped_mentors[c_name]) if grouped_mentors[c_name] else "None"
                students_str = ", ".join(grouped_students[c_name]) if grouped_students[c_name] else "None"
                lines.append(f"**Class: {c_name}**\n• Mentors: {mentors_str}\n• Students: {students_str}")
                
            result = {
                "type": "student_list",
                "data": [{"full_name": u.full_name, "info": f"{c_name} - {role}"} for u, role, c_name in members],
                "message": "\n\n".join(lines)
            }

    elif intent == "pending_approvals":
        if class_id:
            pendings = db.query(User).join(ClassMembership).filter(
                ClassMembership.class_id == class_id,
                ClassMembership.status == 'PENDING'
            ).all()
            result = {
                "type": "student_list",
                "data": [{"full_name": u.full_name, "info": "Pending"} for u in pendings],
                "message": f"Found {len(pendings)} pending approvals."
            }
        else:
            pendings = db.query(User, Class.class_name).join(ClassMembership).join(Class).filter(
                ClassMembership.class_id.in_(class_ids),
                ClassMembership.status == 'PENDING'
            ).all()
            result = {
                "type": "student_list",
                "data": [{"full_name": u.full_name, "info": f"{c_name} - Pending"} for u, c_name in pendings],
                "message": f"Found {len(pendings)} pending approvals across classes."
            }

    elif intent == "mentor_list":
        if class_id:
            mentors = db.query(User).join(ClassMembership).filter(
                ClassMembership.class_id == class_id,
                ClassMembership.member_role == 'MENTOR',
                ClassMembership.status == 'ACTIVE'
            ).all()
            result = {
                "type": "student_list",
                "data": [{"full_name": u.full_name, "info": "Mentor"} for u in mentors],
                "message": f"Found {len(mentors)} mentor(s)."
            }
        else:
            mentors = db.query(User, Class.class_name).join(ClassMembership).join(Class).filter(
                ClassMembership.class_id.in_(class_ids),
                ClassMembership.member_role == 'MENTOR',
                ClassMembership.status == 'ACTIVE'
            ).all()
            result = {
                "type": "student_list",
                "data": [{"full_name": u.full_name, "info": f"{c_name} - Mentor"} for u, c_name in mentors],
                "message": f"Found {len(mentors)} mentor(s) across classes."
            }

    elif intent == "assignment_list":
        if class_id:
            assignments = db.query(Assignment).filter_by(class_id=class_id).order_by(Assignment.created_at.desc()).limit(10).all()
            result = {
                "type": "assignment_list",
                "data": [{"title": a.title, "status": a.status} for a in assignments],
                "message": f"Recent {len(assignments)} assignments."
            }
        else:
            assignments = db.query(Assignment, Class.class_name).join(Class).filter(
                Assignment.class_id.in_(class_ids)
            ).order_by(Assignment.created_at.desc()).limit(10).all()
            result = {
                "type": "assignment_list",
                "data": [{"title": a.title, "status": f"{c_name} - {a.status}"} for a, c_name in assignments],
                "message": f"Recent {len(assignments)} assignments across classes."
            }

    elif intent == "assignment_status":
        assignment_ref = params.get("assignment_ref")
        temporal_ref = params.get("temporal_ref")
        a = get_assignment_by_ref(assignment_ref, temporal_ref)
        if a:
            result = {
                "type": "info",
                "data": [],
                "message": f"Assignment '{a.title}' is currently {a.status}."
            }
        else:
            result = no_data_response("Could not find assignment.")

    elif intent == "assignment_analytics" or intent == "bottleneck_assignments":
        if class_id:
            bottlenecks = db.query(AssignmentAnalytics, Assignment).join(Assignment).filter(
                Assignment.class_id == class_id,
                AssignmentAnalytics.is_bottleneck == True
            ).all()
        else:
            bottlenecks = db.query(AssignmentAnalytics, Assignment).join(Assignment).filter(
                Assignment.class_id.in_(class_ids),
                AssignmentAnalytics.is_bottleneck == True
            ).all()
        result = {
            "type": "assignment_list",
            "data": [{"title": a.title, "info": f"Completion: {aa.completion_rate}%"} for aa, a in bottlenecks],
            "message": f"Found {len(bottlenecks)} bottleneck assignments."
        }

    elif intent == "submission_history":
        student_name = params.get("student_name")
        if not student_name:
            result = no_data_response("Which student?")
        else:
            query = db.query(User).join(ClassMembership)
            if class_id:
                query = query.filter(ClassMembership.class_id == class_id)
            else:
                query = query.filter(ClassMembership.class_id.in_(class_ids))
            student = query.filter(User.full_name.ilike(f"%{student_name}%")).first()
            if student:
                query_subs = db.query(Submission, Assignment).join(Assignment)
                if class_id:
                    query_subs = query_subs.filter(Assignment.class_id == class_id)
                else:
                    query_subs = query_subs.filter(Assignment.class_id.in_(class_ids))
                subs = query_subs.filter(
                    Submission.student_id == student.id,
                    Submission.is_current == True
                ).all()
                result = {
                    "type": "assignment_list",
                    "data": [{"title": a.title, "info": "Late" if s.is_late else "On Time"} for s, a in subs],
                    "message": f"Found {len(subs)} submissions for {student.full_name}."
                }
            else:
                result = no_data_response("Student not found.")

    elif intent == "all_my_classes":
        if caller.role == "ADMIN":
            classes = db.query(Class).filter_by(admin_id=caller.id).all()
        else:
            classes = db.query(Class).join(ClassMembership).filter(ClassMembership.user_id == caller.id).all()
        result = {
            "type": "class_list",
            "data": [{"class_name": c.class_name, "status": c.status} for c in classes],
            "message": f"You have {len(classes)} classes."
        }

    elif intent == "admin_overview" or intent == "class_health":
        if caller.role != "ADMIN":
            result = no_data_response("Admin overview is only available for admins.")
        else:
            ca = db.query(ClassAnalytics, Class).join(Class).filter(Class.admin_id == caller.id).order_by(ClassAnalytics.avg_completion.desc()).all()
            result = {
                "type": "class_list",
                "data": [{"class_name": c.class_name, "info": f"Completion: {ca.avg_completion}%"} for ca, c in ca],
                "message": f"Health overview of {len(ca)} classes."
            }

    elif intent == "general_count":
        if caller and caller.role == "ADMIN":
            total_classes = db.query(Class).filter_by(admin_id=caller.id).count()
            total_students = db.execute(text("""
                SELECT COUNT(DISTINCT cm.user_id)
                FROM class_memberships cm
                JOIN classes c ON c.id = cm.class_id
                WHERE c.admin_id = :admin_id AND cm.member_role = 'STUDENT' AND cm.status = 'ACTIVE'
            """), {"admin_id": str(caller.id)}).scalar()
        else:
            total_classes = 1 if class_id else 0
            total_students = db.query(ClassMembership).filter_by(
                class_id=class_id, member_role='STUDENT', status='ACTIVE'
            ).count() if class_id else 0
            
        result = {
            "type": "count",
            "data": [{"total_classes": total_classes, "total_students": total_students}],
            "message": f"You have {total_classes} class(es) and {total_students} active student(s)."
        }

    else:
        result = no_data_response()
        
    response_payload = {
        "intent": intent,
        "query_text": query_text,
        "result": result,
        "action_links": action_links
    }
    
    _log_query(db, user_id, class_id, query_text, intent, response_payload)
    return response_payload

def _log_query(db: Session, user_id: str, class_id: Optional[str], query_text: str, intent: str, response_payload: dict):
    try:
        log = AiQueryLog(
            requested_by=user_id,
            class_id=class_id,
            query_text=query_text,
            detected_intent=intent,
            response_payload=response_payload
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print("AI log error:", e)
