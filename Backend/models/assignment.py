from sqlalchemy import Column, String, Text, Boolean, CheckConstraint, Index, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base
from datetime import datetime, timezone
import uuid

class Assignment(Base):
    __tablename__ = 'assignments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id = Column(UUID(as_uuid=True), ForeignKey('classes.id', ondelete='CASCADE'), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    content_type = Column(String(10), nullable=False)
    content_url = Column(Text, nullable=True)
    rich_text_body = Column(Text, nullable=True)
    submission_type = Column(String(5), nullable=False)
    deadline_at = Column(DateTime(timezone=True), nullable=True)
    auto_close = Column(Boolean, server_default='false', nullable=False)
    status = Column(String(10), server_default='DRAFT', nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        CheckConstraint("content_type IN ('PDF', 'LINK', 'RICH_TEXT')", name='check_assignment_content'),
        CheckConstraint("submission_type IN ('FILE', 'TEXT', 'BOTH')", name='check_assignment_submission'),
        CheckConstraint("status IN ('DRAFT', 'PUBLISHED', 'CLOSED')", name='check_assignment_status'),
        Index('idx_assignments_class', 'class_id'),
        Index('idx_assignments_status', 'status'),
    )
