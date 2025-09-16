"""Add label column to amis_catalog for structured text representation

Revision ID: 007
Revises: 006
Create Date: 2025-09-16 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add label column for structured text representation
    op.add_column('amis_catalog', sa.Column('label', sa.Text(), nullable=True))

    # Add index on label column for search performance
    op.create_index('ix_amis_catalog_label', 'amis_catalog', ['label'])


def downgrade() -> None:
    # Drop index and column
    op.drop_index('ix_amis_catalog_label', table_name='amis_catalog')
    op.drop_column('amis_catalog', 'label')