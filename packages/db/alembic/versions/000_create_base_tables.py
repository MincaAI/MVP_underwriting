"""create base tables

Revision ID: 000
Revises: 
Create Date: 2025-01-12 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '000'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums using raw SQL to avoid conflicts
    op.execute("CREATE TYPE casestatus AS ENUM ('NEW', 'EXTRACTING', 'TRANSFORMING', 'CODIFYING', 'REVIEW', 'READY', 'EXPORTED', 'ERROR')")
    op.execute("CREATE TYPE component AS ENUM ('EXTRACT', 'TRANSFORM', 'CODIFY', 'EXPORT')")
    op.execute("CREATE TYPE runstatus AS ENUM ('STARTED', 'SUCCESS', 'FAILED', 'ERROR')")
    
    # Create email_message table first (no dependencies)
    op.create_table('email_message',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('from_email', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_message_from_email'), 'email_message', ['from_email'], unique=False)
    op.create_index('ix_email_message_received_at', 'email_message', ['received_at'], unique=False)
    op.create_index('ix_email_message_content_hash', 'email_message', ['content_hash'], unique=False)
    
    # Create email_attachment table
    op.create_table('email_attachment',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email_message_id', sa.Integer(), nullable=False),
        sa.Column('original_name', sa.String(), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(), nullable=False),
        sa.Column('s3_uri', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['email_message_id'], ['email_message.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_attachment_email_message_id'), 'email_attachment', ['email_message_id'], unique=False)
    op.create_index('ix_email_attachment_sha256', 'email_attachment', ['sha256'], unique=False)
    
    # Create case table
    op.create_table('case',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('filename', sa.String(), nullable=True),
        sa.Column('email_message_id', sa.Integer(), nullable=True),
        sa.Column('status', postgresql.ENUM('NEW', 'EXTRACTING', 'TRANSFORMING', 'CODIFYING', 'REVIEW', 'READY', 'EXPORTED', 'ERROR', name='casestatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['email_message_id'], ['email_message.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_case_email_message_id'), 'case', ['email_message_id'], unique=False)
    
    # Create run table
    op.create_table('run',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('case_id', sa.String(), nullable=False),
        sa.Column('component', postgresql.ENUM('EXTRACT', 'TRANSFORM', 'CODIFY', 'EXPORT', name='component', create_type=False), nullable=False),
        sa.Column('profile', sa.String(), nullable=True),
        sa.Column('status', postgresql.ENUM('STARTED', 'SUCCESS', 'FAILED', 'ERROR', name='runstatus', create_type=False), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('file_name', sa.String(), nullable=True),
        sa.Column('file_s3_uri', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['case.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_run_case_id', 'run', ['case_id'], unique=False)
    op.create_index('ix_run_case_component', 'run', ['case_id', 'component'], unique=False)
    
    # Create row table
    op.create_table('row',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('row_index', sa.Integer(), nullable=False),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('extracted_data', sa.JSON(), nullable=True),
        sa.Column('transformed_data', sa.JSON(), nullable=True),
        sa.Column('errors', sa.JSON(), nullable=False),
        sa.Column('warnings', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['run.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'row_index', name='uq_row_run_idx')
    )
    op.create_index('ix_row_run_id', 'row', ['run_id'], unique=False)
    op.create_index('ix_row_row_index', 'row', ['row_index'], unique=False)
    
    # Create codify table
    op.create_table('codify',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('row_idx', sa.Integer(), nullable=False),
        sa.Column('suggested_cvegs', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('candidates', sa.JSON(), nullable=False),
        sa.Column('decision', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['run.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'row_idx', name='uq_codify_run_idx')
    )
    op.create_index('ix_codify_run_id', 'codify', ['run_id'], unique=False)
    op.create_index('ix_codify_row_idx', 'codify', ['row_idx'], unique=False)
    op.create_index('ix_codify_high_conf', 'codify', ['confidence'], unique=False)
    
    # Create correction table
    op.create_table('correction',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('row_idx', sa.Integer(), nullable=False),
        sa.Column('from_code', sa.String(), nullable=True),
        sa.Column('to_code', sa.String(), nullable=False),
        sa.Column('corrected_at', sa.DateTime(), nullable=False),
        sa.Column('corrected_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['run.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create amis_record table
    op.create_table('amis_record',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cvegs', sa.String(), nullable=False),
        sa.Column('brand', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('body_type', sa.String(), nullable=True),
        sa.Column('use_type', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cvegs', name='uq_amis_record_cvegs')
    )
    op.create_index('ix_amis_record_cvegs', 'amis_record', ['cvegs'], unique=True)
    op.create_index('ix_amis_record_brand', 'amis_record', ['brand'], unique=False)
    op.create_index('ix_amis_record_model', 'amis_record', ['model'], unique=False)
    op.create_index('ix_amis_record_year', 'amis_record', ['year'], unique=False)
    op.create_index('ix_amis_record_body_type', 'amis_record', ['body_type'], unique=False)
    op.create_index('ix_amis_record_use_type', 'amis_record', ['use_type'], unique=False)
    op.create_index('ix_amis_brand_model_year', 'amis_record', ['brand', 'model', 'year'], unique=False)
    op.create_index('ix_amis_description', 'amis_record', ['description'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('amis_record')
    op.drop_table('correction')
    op.drop_table('codify')
    op.drop_table('row')
    op.drop_table('run')
    op.drop_table('case')
    op.drop_table('email_attachment')
    op.drop_table('email_message')
    
    # Drop enums
    runstatus = postgresql.ENUM('STARTED', 'SUCCESS', 'FAILED', 'ERROR', name='runstatus')
    runstatus.drop(op.get_bind())
    
    component = postgresql.ENUM('EXTRACT', 'TRANSFORM', 'CODIFY', 'EXPORT', name='component')
    component.drop(op.get_bind())
    
    casestatus = postgresql.ENUM('NEW', 'EXTRACTING', 'TRANSFORMING', 'CODIFYING', 'REVIEW', 'READY', 'EXPORTED', 'ERROR', name='casestatus')
    casestatus.drop(op.get_bind())
