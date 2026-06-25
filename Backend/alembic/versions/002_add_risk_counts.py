"""add medium and low risk count to class_analytics

Revision ID: 002_add_risk_counts
Revises: abc123_initial_schema
Create Date: 2026-06-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002_add_risk_counts'
down_revision = 'abc123_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add medium_risk_count and low_risk_count columns to class_analytics
    op.add_column('class_analytics', sa.Column('medium_risk_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('class_analytics', sa.Column('low_risk_count', sa.Integer(), server_default='0', nullable=False))

def downgrade() -> None:
    op.drop_column('class_analytics', 'low_risk_count')
    op.drop_column('class_analytics', 'medium_risk_count')
