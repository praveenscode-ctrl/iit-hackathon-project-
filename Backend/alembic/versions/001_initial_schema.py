"""initial_schema

Revision ID: abc123_initial_schema
Revises: 
Create Date: 2026-06-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from database import engine, Base
import models

# revision identifiers, used by Alembic.
revision = 'abc123_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Phase 1 instruction explicitly says to run Base.metadata.create_all
    Base.metadata.create_all(engine)

def downgrade() -> None:
    Base.metadata.drop_all(engine)
