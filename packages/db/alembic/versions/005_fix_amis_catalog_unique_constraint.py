"""Fix amis_catalog unique constraint to include modelo (year)

Revision ID: 005
Revises: 004
Create Date: 2025-09-16 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the constraint exists before dropping it
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Get existing constraints on the amis_catalog table
    constraints = inspector.get_unique_constraints('amis_catalog')
    constraint_names = [c['name'] for c in constraints]
    
    # Drop existing unique constraint only if it exists
    if 'uq_amis_catalog_version_cvegs' in constraint_names:
        op.drop_constraint('uq_amis_catalog_version_cvegs', 'amis_catalog', type_='unique')

    # Create new unique constraint including modelo (year) if it doesn't already exist
    if 'uq_amis_catalog_version_cvegs_modelo' not in constraint_names:
        op.create_unique_constraint(
            'uq_amis_catalog_version_cvegs_modelo',
            'amis_catalog',
            ['catalog_version', 'cvegs', 'modelo']
        )


def downgrade() -> None:
    # Drop new constraint
    op.drop_constraint('uq_amis_catalog_version_cvegs_modelo', 'amis_catalog', type_='unique')

    # Recreate old constraint
    op.create_unique_constraint(
        'uq_amis_catalog_version_cvegs',
        'amis_catalog',
        ['catalog_version', 'cvegs']
    )
