from sqlalchemy import Column, String, Boolean, CheckConstraint, Index, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base
import uuid

class StudentAnalytics(Base):
    __tablename__ = 'student_analytics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    class_id = Column(UUID(as_uuid=True), ForeignKey('classes.id', ondelete='CASCADE'), nullable=False)
    total_assigned = Column(Integer, server_default='0', nullable=False)
    total_submitted = Column(Integer, server_default='0', nullable=False)
    total_missed = Column(Integer, server_default='0', nullable=False)
    total_late = Column(Integer, server_default='0', nullable=False)
    completion_rate = Column(Numeric(5, 2), server_default='0', nullable=False)
    current_streak = Column(Integer, server_default='0', nullable=False)
    longest_streak = Column(Integer, server_default='0', nullable=False)
    avg_submission_delay_hours = Column(Numeric(6, 2), nullable=True)
    risk_level = Column(String(12), server_default='NORMAL', nullable=False)
    consecutive_misses = Column(Integer, server_default='0', nullable=False)
    last_computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        CheckConstraint("risk_level IN ('NORMAL', 'LOW', 'MEDIUM', 'HIGH', 'RECOVERING')", name='check_sa_risk'),
        UniqueConstraint('student_id', 'class_id', name='uq_sa_student_class'),
        Index('idx_sa_student', 'student_id'),
        Index('idx_sa_class', 'class_id'),
        Index('idx_sa_risk', 'risk_level'),
    )

class ClassAnalytics(Base):
    __tablename__ = 'class_analytics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id = Column(UUID(as_uuid=True), ForeignKey('classes.id', ondelete='CASCADE'), unique=True, nullable=False)
    total_students = Column(Integer, server_default='0', nullable=False)
    total_assignments = Column(Integer, server_default='0', nullable=False)
    avg_completion = Column(Numeric(5, 2), server_default='0', nullable=False)
    avg_miss_rate = Column(Numeric(5, 2), server_default='0', nullable=False)
    avg_late_rate = Column(Numeric(5, 2), server_default='0', nullable=False)
    high_risk_count = Column(Integer, server_default='0', nullable=False)
    last_computed_at = Column(DateTime(timezone=True), nullable=True)

class AssignmentAnalytics(Base):
    __tablename__ = 'assignment_analytics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey('assignments.id', ondelete='CASCADE'), unique=True, nullable=False)
    total_targets = Column(Integer, server_default='0', nullable=False)
    submitted_count = Column(Integer, server_default='0', nullable=False)
    missed_count = Column(Integer, server_default='0', nullable=False)
    late_count = Column(Integer, server_default='0', nullable=False)
    completion_rate = Column(Numeric(5, 2), server_default='0', nullable=False)
    is_bottleneck = Column(Boolean, server_default='false', nullable=False)
    last_computed_at = Column(DateTime(timezone=True), nullable=True)
