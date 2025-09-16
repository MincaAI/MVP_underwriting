"""Update amis_catalog schema to match CATVER_ENVIOS.xlsx structure

Revision ID: 004
Revises: 003
Create Date: 2025-09-16 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing amis_catalog table and recreate with proper CATVER schema
    op.drop_index('ix_amis_version_brand_year', table_name='amis_catalog')
    op.drop_table('amis_catalog')

    # Create new amis_catalog table with full CATVER schema
    op.create_table(
        'amis_catalog',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('catalog_version', sa.Text(), nullable=False),
        # CATVER-specific columns (matching Excel structure)
        sa.Column('marca', sa.String(length=25), nullable=False),
        sa.Column('submarca', sa.String(length=52), nullable=False),
        sa.Column('numver', sa.Integer(), nullable=False),
        sa.Column('ramo', sa.Integer(), nullable=False),
        sa.Column('cvemarc', sa.Integer(), nullable=False),
        sa.Column('cvesubm', sa.Integer(), nullable=False),
        sa.Column('martip', sa.Integer(), nullable=False),
        sa.Column('cvesegm', sa.String(length=51), nullable=False),
        sa.Column('modelo', sa.Integer(), nullable=False),  # Year in CATVER
        sa.Column('cvegs', sa.Integer(), nullable=False),
        sa.Column('descveh', sa.String(length=150), nullable=False),
        sa.Column('idperdiod', sa.Integer(), nullable=False),
        sa.Column('sumabas', sa.Float(), nullable=False),
        sa.Column('tipveh', sa.String(length=19), nullable=False),
        # ML and metadata columns
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        # Constraints
        sa.UniqueConstraint('catalog_version', 'cvegs', 'modelo', name='uq_amis_catalog_version_cvegs_modelo')
    )

    # Create indexes for efficient querying
    op.create_index('ix_amis_catalog_version_brand_year', 'amis_catalog', ['catalog_version', 'marca', 'modelo'], unique=False)
    op.create_index('ix_amis_catalog_cvegs', 'amis_catalog', ['cvegs'], unique=False)
    op.create_index('ix_amis_catalog_marca', 'amis_catalog', ['marca'], unique=False)
    op.create_index('ix_amis_catalog_submarca', 'amis_catalog', ['submarca'], unique=False)
    op.create_index('ix_amis_catalog_modelo', 'amis_catalog', ['modelo'], unique=False)
    op.create_index('ix_amis_catalog_description', 'amis_catalog', ['descveh'], unique=False)
    op.create_index('ix_amis_catalog_tipveh', 'amis_catalog', ['tipveh'], unique=False)


def downgrade() -> None:
    # Drop new table and recreate old simplified schema
    op.drop_index('ix_amis_catalog_tipveh', table_name='amis_catalog')
    op.drop_index('ix_amis_catalog_description', table_name='amis_catalog')
    op.drop_index('ix_amis_catalog_modelo', table_name='amis_catalog')
    op.drop_index('ix_amis_catalog_submarca', table_name='amis_catalog')
    op.drop_index('ix_amis_catalog_marca', table_name='amis_catalog')
    op.drop_index('ix_amis_catalog_cvegs', table_name='amis_catalog')
    op.drop_index('ix_amis_catalog_version_brand_year', table_name='amis_catalog')
    op.drop_table('amis_catalog')

    # Recreate old simplified schema
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

    op.create_index('ix_amis_version_brand_year', 'amis_catalog', ['catalog_version', 'brand', 'year'], unique=False)