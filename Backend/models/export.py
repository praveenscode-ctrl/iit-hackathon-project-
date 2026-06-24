from sqlalchemy import Column, String, Text, CheckConstraint, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from database import Base
import uuid

class ExportJob(Base):
    __tablename__ = 'export_jobs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requested_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey('assignments.id', ondelete='CASCADE'), nullable=True)
    export_type = Column(String(30), nullable=False)
    format = Column(String(5), server_default='XLSX', nullable=False)
    status = Column(String(10), server_default='PENDING', nullable=False)
    file_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        CheckConstraint("export_type IN ('ASSIGNMENT_TRACKER')", name='check_ex_type'),
        CheckConstraint("status IN ('PENDING', 'DONE', 'FAILED')", name='check_ex_status'),
    )

class AiQueryLog(Base):
    __tablename__ = 'ai_query_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requested_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    class_id = Column(UUID(as_uuid=True), ForeignKey('classes.id', ondelete='SET NULL'), nullable=True)
    query_text = Column(Text, nullable=False)
    detected_intent = Column(String(50), nullable=True)
    filters = Column(JSONB, nullable=True)
    response_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
