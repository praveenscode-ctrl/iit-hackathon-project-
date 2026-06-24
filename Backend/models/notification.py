from sqlalchemy import Column, String, Text, Boolean, CheckConstraint, Index, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from database import Base
import uuid

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    notification_type = Column(String(30), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=True)
    is_read = Column(Boolean, server_default='false', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        CheckConstraint("notification_type IN ('STUDENT_APPROVED', 'STUDENT_REJECTED', 'ASSIGNMENT_PUBLISHED', 'DEADLINE_REMINDER', 'SUBMISSION_RECEIPT', 'MISSED_DEADLINE', 'RISK_ALERT', 'CO_MENTOR_ADDED', 'CLASS_ARCHIVED')", name='check_notif_type'),
        Index('idx_notif_user', 'user_id'),
        Index('idx_notif_read', 'is_read'),
    )

class ReminderJob(Base):
    __tablename__ = 'reminder_jobs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey('assignments.id', ondelete='CASCADE'), nullable=False)
    remind_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(12), server_default='SCHEDULED', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        CheckConstraint("status IN ('SCHEDULED', 'TRIGGERED', 'CANCELLED')", name='check_rem_status'),
    )
