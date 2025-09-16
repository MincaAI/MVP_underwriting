"""Drop catver_record table - consolidate to amis_catalog only

Revision ID: 003
Revises: cafe0c0dea12
Create Date: 2025-09-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = 'cafe0c0dea12'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop catver_record table - using amis_catalog as single source of truth."""

    # Use raw SQL to safely drop table and indexes if they exist
    connection = op.get_bind()

    # Drop indexes if they exist (ignore errors if they don't)
    try:
        connection.execute(sa.text("DROP INDEX IF EXISTS ix_catver_record_submarca"))
        connection.execute(sa.text("DROP INDEX IF EXISTS ix_catver_record_modelo"))
        connection.execute(sa.text("DROP INDEX IF EXISTS ix_catver_record_marca"))
        connection.execute(sa.text("DROP INDEX IF EXISTS ix_catver_record_cvegs"))
        connection.execute(sa.text("DROP INDEX IF EXISTS ix_catver_description"))
        connection.execute(sa.text("DROP INDEX IF EXISTS ix_catver_brand_model_year"))
    except Exception:
        pass  # Ignore errors if indexes don't exist

    # Drop the table if it exists
    try:
        connection.execute(sa.text("DROP TABLE IF EXISTS catver_record CASCADE"))
    except Exception:
        pass  # Ignore errors if table doesn't exist


def downgrade() -> None:
    """Recreate catver_record table if needed (not recommended)."""

    # Recreate table with pgvector import
    import pgvector.sqlalchemy

    op.create_table('catver_record',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('marca', sa.String(length=25), nullable=False),
        sa.Column('submarca', sa.String(length=52), nullable=False),
        sa.Column('numver', sa.Integer(), nullable=False),
        sa.Column('ramo', sa.Integer(), nullable=False),
        sa.Column('cvemarc', sa.Integer(), nullable=False),
        sa.Column('cvesubm', sa.Integer(), nullable=False),
        sa.Column('martip', sa.Integer(), nullable=False),
        sa.Column('cvesegm', sa.String(length=51), nullable=False),
        sa.Column('modelo', sa.Integer(), nullable=False),
        sa.Column('cvegs', sa.Integer(), nullable=False),
        sa.Column('descveh', sa.String(length=150), nullable=False),
        sa.Column('idperdiod', sa.Integer(), nullable=False),
        sa.Column('sumabas', sa.Float(), nullable=False),
        sa.Column('tipveh', sa.String(length=19), nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Recreate indexes
    op.create_index('ix_catver_brand_model_year', 'catver_record', ['marca', 'submarca', 'modelo'], unique=False)
    op.create_index('ix_catver_description', 'catver_record', ['descveh'], unique=False)
    op.create_index('ix_catver_record_cvegs', 'catver_record', ['cvegs'], unique=True)
    op.create_index('ix_catver_record_marca', 'catver_record', ['marca'], unique=False)
    op.create_index('ix_catver_record_modelo', 'catver_record', ['modelo'], unique=False)
    op.create_index('ix_catver_record_submarca', 'catver_record', ['submarca'], unique=False)