"""Update embedding dimension to 1024 for multilingual-e5-large

Revision ID: f195a7f7f69d
Revises: 007
Create Date: 2025-09-21 03:17:16.573890

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f195a7f7f69d'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update embedding column dimension from 384 to 1024 for multilingual-e5-large
    op.execute("ALTER TABLE amis_catalog ALTER COLUMN embedding TYPE vector(1024)")


def downgrade() -> None:
    # Revert embedding column dimension back to 384
    op.execute("ALTER TABLE amis_catalog ALTER COLUMN embedding TYPE vector(384)")