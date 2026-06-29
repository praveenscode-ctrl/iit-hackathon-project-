from sqlalchemy import Column, String, Text, Boolean, CheckConstraint, Index, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base
import uuid

class Submission(Base):
    __tablename__ = 'submissions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey('assignments.id', ondelete='CASCADE'), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    submission_type = Column(String(5), nullable=False)
    file_url = Column(Text, nullable=True)
    text_answer = Column(Text, nullable=True)
    is_late = Column(Boolean, server_default='false', nullable=False)
    late_reason = Column(Text, nullable=True)
    version = Column(Integer, server_default='1', nullable=False)
    is_current = Column(Boolean, server_default='true', nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        CheckConstraint("submission_type IN ('FILE', 'TEXT')", name='check_sub_type'),
        UniqueConstraint('assignment_id', 'student_id', 'version', name='uq_submission_version'),
        Index('idx_submissions_assignment', 'assignment_id'),
        Index('idx_submissions_student', 'student_id'),
        Index('idx_submissions_current', 'is_current'),
    )

class ExtensionRequest(Base):
    __tablename__ = 'extension_requests'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey('assignments.id', ondelete='CASCADE'), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(10), server_default='PENDING', nullable=False) # PENDING, APPROVED, REJECTED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED')", name='check_extension_status'),
        UniqueConstraint('assignment_id', 'student_id', name='uq_extension_request'),
    )
