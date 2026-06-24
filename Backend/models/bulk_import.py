from sqlalchemy import Column, String, Text, CheckConstraint, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base
import uuid

class BulkImportBatch(Base):
    __tablename__ = 'bulk_import_batches'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    file_name = Column(String(255), nullable=True)
    status = Column(String(20), server_default='UPLOADED', nullable=False)
    total_rows = Column(Integer, server_default='0', nullable=False)
    success_rows = Column(Integer, server_default='0', nullable=False)
    failed_rows = Column(Integer, server_default='0', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        CheckConstraint("status IN ('UPLOADED', 'VALIDATING', 'PARTIAL', 'COMPLETED', 'FAILED')", name='check_bi_status'),
    )

class BulkImportError(Base):
    __tablename__ = 'bulk_import_errors'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('bulk_import_batches.id', ondelete='CASCADE'), nullable=False)
    sheet_name = Column(String(20), nullable=False)
    row_number = Column(Integer, nullable=False)
    field_name = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
