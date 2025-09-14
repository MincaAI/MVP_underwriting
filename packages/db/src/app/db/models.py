import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, JSON, Float, Text,
    Enum, Boolean, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base
from pgvector.sqlalchemy import Vector

# --- enums ---
class CaseStatus(str, enum.Enum):
    NEW = "NEW"
    EXTRACTING = "EXTRACTING"
    TRANSFORMING = "TRANSFORMING"
    CODIFYING = "CODIFYING"
    REVIEW = "REVIEW"
    READY = "READY"
    EXPORTED = "EXPORTED"
    ERROR = "ERROR"

class Component(str, enum.Enum):
    EXTRACT = "EXTRACT"    # worker-extractor
    TRANSFORM = "TRANSFORM"
    CODIFY = "CODIFY"
    EXPORT = "EXPORT"

class RunStatus(str, enum.Enum):
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ERROR = "ERROR"  # Added for consistency with document processor

# --- core tables ---
class Case(Base):
    __tablename__ = "case"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)  # uuid str
    source: Mapped[str] = mapped_column(String, nullable=True) # 'upload'/'email'
    filename: Mapped[str] = mapped_column(String, nullable=True)
    email_message_id: Mapped[int] = mapped_column(ForeignKey("email_message.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), default=CaseStatus.NEW, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    runs: Mapped[list["Run"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    email_message: Mapped["EmailMessage"] = relationship(back_populates="cases")

class Run(Base):
    __tablename__ = "run"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)  # uuid str
    case_id: Mapped[str] = mapped_column(ForeignKey("case.id", ondelete="CASCADE"), index=True)
    component: Mapped[Component] = mapped_column(Enum(Component), nullable=False)
    profile: Mapped[str] = mapped_column(String, nullable=True)   # broker profile name
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.STARTED)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    file_name: Mapped[str] = mapped_column(String, nullable=True)  # Added for document processor
    file_s3_uri: Mapped[str] = mapped_column(String, nullable=True)  # Added for document processor
    error_message: Mapped[str] = mapped_column(Text, nullable=True)  # Added for error tracking
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # Added for tracking

    case: Mapped["Case"] = relationship(back_populates="runs")
    rows: Mapped[list["Row"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    codify_results: Mapped[list["Codify"]] = relationship(back_populates="run", cascade="all, delete-orphan")

Index("ix_run_case_component", Run.case_id, Run.component)

class Row(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"), index=True)
    row_index: Mapped[int] = mapped_column(Integer, index=True)  # Changed from row_idx for consistency
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=True)      # Original Excel/CSV row data
    extracted_data: Mapped[dict] = mapped_column(JSON, nullable=True)  # Cleaned extracted data
    transformed_data: Mapped[dict] = mapped_column(JSON, nullable=True)  # Normalized for matching
    errors: Mapped[dict] = mapped_column(JSON, default=dict)
    warnings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    run: Mapped["Run"] = relationship(back_populates="rows")
    __table_args__ = (UniqueConstraint("run_id", "row_index", name="uq_row_run_idx"),)

class Codify(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"), index=True)
    row_idx: Mapped[int] = mapped_column(Integer, index=True)
    suggested_cvegs: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(Float)   # 0..1
    candidates: Mapped[dict] = mapped_column(JSON)     # [{cvegs, label, score}, ...]
    decision: Mapped[str] = mapped_column(String)      # 'auto_accept' | 'needs_review' | 'no_match'

    run: Mapped["Run"] = relationship(back_populates="codify_results")
    __table_args__ = (UniqueConstraint("run_id", "row_idx", name="uq_codify_run_idx"),)

Index("ix_codify_high_conf", Codify.confidence)

class Correction(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"), index=True)
    row_idx: Mapped[int] = mapped_column(Integer, index=True)
    from_code: Mapped[str | None] = mapped_column(String, nullable=True)
    to_code: Mapped[str] = mapped_column(String)
    corrected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    corrected_by: Mapped[str] = mapped_column(String, nullable=True)

    run: Mapped["Run"] = relationship()

# --- email processing tables ---
class EmailMessage(Base):
    __tablename__ = "email_message"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    attachments: Mapped[list["EmailAttachment"]] = relationship(back_populates="email_message", cascade="all, delete-orphan")
    cases: Mapped[list["Case"]] = relationship(back_populates="email_message")

class EmailAttachment(Base):
    __tablename__ = "email_attachment"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email_message_id: Mapped[int] = mapped_column(ForeignKey("email_message.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False, index=True)
    s3_uri: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    email_message: Mapped["EmailMessage"] = relationship(back_populates="attachments")

# --- AMIS catalog tables ---
class AmisRecord(Base):
    __tablename__ = "amis_record"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cvegs: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    brand: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model: Mapped[str] = mapped_column(String, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    body_type: Mapped[str] = mapped_column(String, nullable=True, index=True)
    use_type: Mapped[str] = mapped_column(String, nullable=True, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(384), nullable=True)  # For semantic search
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Index("ix_amis_brand_model_year", AmisRecord.brand, AmisRecord.model, AmisRecord.year)
Index("ix_amis_description", AmisRecord.description)

# Backward compatibility alias for older imports
AmisCatalog = AmisRecord
