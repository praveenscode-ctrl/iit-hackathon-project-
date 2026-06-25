from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class AssignmentHistoryItem(BaseModel):
    assignment_id: str
    title: str
    deadline_at: Optional[datetime]
    tracker_status: str
    submitted_at: Optional[datetime]
    is_late: bool

class StudentAnalyticsResponse(BaseModel):
    student_id: str
    full_name: str
    class_id: str
    class_name: str
    total_assigned: int
    total_submitted: int
    total_missed: int
    total_late: int
    completion_rate: float
    current_streak: int
    longest_streak: int
    consecutive_misses: int
    avg_submission_delay_hours: Optional[float]
    risk_level: str
    class_avg_completion: float
    assignment_history: List[AssignmentHistoryItem]
    last_computed_at: Optional[datetime]

class ClassAnalyticsResponse(BaseModel):
    class_id: str
    class_name: str
    total_students: int
    total_assignments: int
    avg_completion: float
    avg_miss_rate: float
    avg_late_rate: float
    high_risk_count: int
    last_computed_at: Optional[datetime]
    risk_distribution: Dict[str, int]
    bottleneck_assignments: List[Dict[str, Any]]

class AdminOverviewResponse(BaseModel):
    total_classes: int
    total_mentors: int
    total_students: int
    total_assignments: int
    classes: List[dict]
