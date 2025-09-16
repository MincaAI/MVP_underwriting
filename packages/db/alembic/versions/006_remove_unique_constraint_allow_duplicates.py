"""Remove unique constraint to allow duplicate CVEGS entries

Revision ID: 006
Revises: 005
Create Date: 2025-09-16 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the unique constraint - allow duplicate CVEGS entries
    # This is needed because CATVER Excel has legitimate duplicates
    # (different variants of same vehicle in same year)
    op.drop_constraint('uq_amis_catalog_version_cvegs_modelo', 'amis_catalog', type_='unique')


def downgrade() -> None:
    # Recreate unique constraint
    op.create_unique_constraint(
        'uq_amis_catalog_version_cvegs_modelo',
        'amis_catalog',
        ['catalog_version', 'cvegs', 'modelo']
    )