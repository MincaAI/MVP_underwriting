"""create amis catalog tables and settings

Revision ID: cafe0c0dea12
Revises: b18d56f08e82
Create Date: 2025-09-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision = 'cafe0c0dea12'
down_revision = 'b18d56f08e82'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        'catalog_import',
        sa.Column('version', sa.Text(), primary_key=True, nullable=False),
        sa.Column('s3_uri', sa.Text(), nullable=False),
        sa.Column('sha256', sa.Text(), nullable=False),
        sa.Column('rows_loaded', sa.Integer(), nullable=True),
        sa.Column('model_id', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('UPLOADED','LOADED','EMBEDDED','ACTIVE','FAILED')", name='ck_catalog_import_status')
    )

    op.create_table(
        'amis_catalog',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('catalog_version', sa.Text(), nullable=False),
        sa.Column('cvegs', sa.Text(), nullable=False),
        sa.Column('brand', sa.Text(), nullable=True),
        sa.Column('model', sa.Text(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('use', sa.Text(), nullable=True),
        sa.Column('label', sa.Text(), nullable=False),
        sa.Column('aliases', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=True),
        sa.UniqueConstraint('catalog_version', 'cvegs', name='uq_amis_catalog_version_cvegs')
    )

    op.create_table(
        'app_settings',
        sa.Column('key', sa.Text(), primary_key=True, nullable=False),
        sa.Column('value', sa.Text(), nullable=False)
    )

    op.create_index('ix_amis_version_brand_year', 'amis_catalog', ['catalog_version', 'brand', 'year'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_amis_version_brand_year', table_name='amis_catalog')
    op.drop_table('app_settings')
    op.drop_table('amis_catalog')
    op.drop_table('catalog_import')

