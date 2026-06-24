from sqlalchemy import Column, String, Text, Boolean, CheckConstraint, Index, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base
import uuid

class Class(Base):
    __tablename__ = 'classes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    class_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    academic_year = Column(String(20), nullable=True)
    status = Column(String(10), server_default='ACTIVE', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name='check_class_status'),
        Index('idx_classes_admin', 'admin_id'),
    )

class ClassMembership(Base):
    __tablename__ = 'class_memberships'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id = Column(UUID(as_uuid=True), ForeignKey('classes.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    member_role = Column(String(10), nullable=False)
    is_primary_mentor = Column(Boolean, server_default='false', nullable=False)
    joined_via = Column(String(15), nullable=False)
    status = Column(String(10), server_default='PENDING', nullable=False)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        CheckConstraint("member_role IN ('MENTOR', 'STUDENT')", name='check_cm_role'),
        CheckConstraint("joined_via IN ('MANUAL', 'BULK_IMPORT')", name='check_cm_joined_via'),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'PENDING', 'REJECTED')", name='check_cm_status'),
        Index('idx_cm_class', 'class_id'),
        Index('idx_cm_user', 'user_id'),
        Index('idx_cm_status', 'status'),
    )
