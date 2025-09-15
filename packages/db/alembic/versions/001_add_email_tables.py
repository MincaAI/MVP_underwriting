"""add email_message and email_attachment tables

Revision ID: 001
Revises: 
Create Date: 2025-01-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = '000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration is now redundant as all tables are created in 000_create_base_tables
    # Keeping this as a placeholder for future email-related schema changes
    pass


def downgrade() -> None:
    # This migration is now redundant as all tables are created in 000_create_base_tables
    # Keeping this as a placeholder for future email-related schema changes
    pass
