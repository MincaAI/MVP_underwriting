"""add pre-analysis fields to case table

Revision ID: 002
Revises: 001
Create Date: 2025-09-14 20:17:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add pre-analysis fields to case table
    op.add_column('case', sa.Column('pre_analysis_status', sa.String(20), nullable=False, server_default='pending'))
    op.add_column('case', sa.Column('pre_analysis_completed_at', sa.DateTime(), nullable=True))
    op.add_column('case', sa.Column('missing_requirements', sa.JSON(), nullable=True))
    op.add_column('case', sa.Column('pre_analysis_notes', sa.Text(), nullable=True))
    
    # Create index for pre_analysis_status for better query performance
    op.create_index('ix_case_pre_analysis_status', 'case', ['pre_analysis_status'], unique=False)


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_case_pre_analysis_status', table_name='case')
    
    # Drop columns in reverse order
    op.drop_column('case', 'pre_analysis_notes')
    op.drop_column('case', 'missing_requirements')
    op.drop_column('case', 'pre_analysis_completed_at')
    op.drop_column('case', 'pre_analysis_status')
