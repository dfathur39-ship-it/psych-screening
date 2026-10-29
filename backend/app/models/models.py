import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Boolean, ForeignKey, DateTime, Text, Enum,
    UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class SessionStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


class AdminRole(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"
    psychologist = "psychologist"


class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    nama_jabatan = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    position_questions = relationship("PositionQuestion", back_populates="position", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    question_text = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    answer_options = relationship("AnswerOption", back_populates="question", cascade="all, delete-orphan",
                                   order_by="AnswerOption.order_number")
    position_links = relationship("PositionQuestion", back_populates="question", cascade="all, delete-orphan")


class PositionQuestion(Base):
    __tablename__ = "position_questions"
    __table_args__ = (UniqueConstraint("position_id", "question_id", name="uq_position_question"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    position_id = Column(UUID(as_uuid=False), ForeignKey("positions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(UUID(as_uuid=False), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    order_number = Column(Integer, nullable=False, default=0)

    position = relationship("Position", back_populates="position_questions")
    question = relationship("Question", back_populates="position_links")


class AnswerOption(Base):
    __tablename__ = "answer_options"
    __table_args__ = (
        UniqueConstraint("question_id", "option_code", name="uq_question_option_code"),
        CheckConstraint("option_code in ('A','B','C','D')", name="ck_option_code_valid"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    question_id = Column(UUID(as_uuid=False), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    option_code = Column(String(1), nullable=False)
    option_text = Column(Text, nullable=False)
    score = Column(Integer, nullable=False, default=0)
    order_number = Column(Integer, nullable=False, default=0)

    question = relationship("Question", back_populates="answer_options")


class Participant(Base):
    __tablename__ = "participants"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    nama = Column(String(255), nullable=False)
    usia = Column(Integer, nullable=False)
    divisi = Column(String(255), nullable=True)  # legacy: no longer collected
    jabatan = Column(String(255), nullable=False)
    no_hp = Column(String(30), nullable=False)
    email = Column(String(255), nullable=True)  # nullable only for rows created before email was collected
    nik = Column(String(32), nullable=True)  # encrypted-at-rest via app layer / masked on output
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    ktp_document = relationship("KtpDocument", back_populates="participant", uselist=False,
                                 cascade="all, delete-orphan")
    screening_sessions = relationship("ScreeningSession", back_populates="participant")

    __table_args__ = (Index("ix_participants_nik", "nik"),)


class KtpDocument(Base):
    """Stores OCR result + file reference. File itself lives in private storage,
    never served via public URL. Can be purged after OCR per retention policy."""
    __tablename__ = "ktp_documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    participant_id = Column(UUID(as_uuid=False), ForeignKey("participants.id", ondelete="CASCADE"),
                             nullable=False, unique=True)
    file_path = Column(String(500), nullable=True)  # nullable = deleted after OCR per retention
    file_deleted = Column(Boolean, nullable=False, default=False)
    ocr_raw_text = Column(Text, nullable=True)
    ocr_confidence = Column(Integer, nullable=True)  # 0-100
    ocr_provider = Column(String(20), nullable=True)  # tesseract | vlm (provider yang benar-benar dipakai)
    ocr_fallback_used = Column(Boolean, nullable=False, default=False)
    tempat_lahir = Column(String(255), nullable=True)
    tanggal_lahir = Column(String(20), nullable=True)
    jenis_kelamin = Column(String(20), nullable=True)
    alamat = Column(Text, nullable=True)
    rt_rw = Column(String(20), nullable=True)
    kelurahan = Column(String(255), nullable=True)
    kecamatan = Column(String(255), nullable=True)
    agama = Column(String(50), nullable=True)
    status_perkawinan = Column(String(50), nullable=True)
    pekerjaan_ktp = Column(String(255), nullable=True)
    kewarganegaraan = Column(String(50), nullable=True)
    corrected_by_user = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    participant = relationship("Participant", back_populates="ktp_document")


class ResultCategory(Base):
    __tablename__ = "result_categories"
    __table_args__ = (CheckConstraint("min_score <= max_score", name="ck_result_category_range_valid"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    min_score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScreeningSession(Base):
    __tablename__ = "screening_sessions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    participant_id = Column(UUID(as_uuid=False), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    position_id = Column(UUID(as_uuid=False), ForeignKey("positions.id", ondelete="SET NULL"), nullable=True)
    total_score = Column(Integer, nullable=True)
    result_category_id = Column(UUID(as_uuid=False), ForeignKey("result_categories.id", ondelete="SET NULL"),
                                 nullable=True)
    status = Column(Enum(SessionStatus, name="session_status"), nullable=False, default=SessionStatus.in_progress)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    participant = relationship("Participant", back_populates="screening_sessions")
    position = relationship("Position")
    result_category = relationship("ResultCategory")
    answers = relationship("ScreeningAnswer", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_sessions_participant", "participant_id"),)


class ScreeningAnswer(Base):
    __tablename__ = "screening_answers"
    __table_args__ = (UniqueConstraint("screening_session_id", "question_id", name="uq_session_question_answer"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    screening_session_id = Column(UUID(as_uuid=False), ForeignKey("screening_sessions.id", ondelete="CASCADE"),
                                   nullable=False)
    question_id = Column(UUID(as_uuid=False), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    answer_option_id = Column(UUID(as_uuid=False), ForeignKey("answer_options.id", ondelete="CASCADE"),
                               nullable=False)
    score = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ScreeningSession", back_populates="answers")
    question = relationship("Question")
    answer_option = relationship("AnswerOption")


class Admin(Base):
    __tablename__ = "admins"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(AdminRole, name="admin_role"), nullable=False, default=AdminRole.admin)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    audit_logs = relationship("AuditLog", back_populates="admin")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    admin_id = Column(UUID(as_uuid=False), ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    admin = relationship("Admin", back_populates="audit_logs")
    action = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=True)
    target_id = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def _utcnow():
    return datetime.now(timezone.utc)


class SupportThread(Base):
    """A help/contact conversation between an (anonymous) visitor and admins.
    Visitors have no account: they hold a random secret token (only its SHA-256
    hash is stored) that authorises access to their own thread."""
    __tablename__ = "support_threads"
    __table_args__ = (
        CheckConstraint("status in ('open','closed')", name="ck_support_thread_status"),
        Index("ix_support_threads_status_last", "status", "last_message_at"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    visitor_name = Column(String(100), nullable=False)
    visitor_contact = Column(String(150), nullable=True)
    token_hash = Column(String(64), nullable=False)
    status = Column(String(10), nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    last_message_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    messages = relationship("SupportMessage", back_populates="thread", cascade="all, delete-orphan",
                             order_by="SupportMessage.created_at")


class SupportMessage(Base):
    __tablename__ = "support_messages"
    __table_args__ = (
        CheckConstraint("sender in ('visitor','admin')", name="ck_support_message_sender"),
        Index("ix_support_messages_thread_created", "thread_id", "created_at"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    thread_id = Column(UUID(as_uuid=False), ForeignKey("support_threads.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(10), nullable=False)
    admin_id = Column(UUID(as_uuid=False), ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)  # set when an admin has read a visitor message

    thread = relationship("SupportThread", back_populates="messages")
    admin = relationship("Admin")


class RetakeRequest(Base):
    """A participant's request to redo a completed screening. Requires admin approval;
    an approved request is consumed (status -> used) the moment a new session is started,
    so a further retake always needs a fresh request."""
    __tablename__ = "retake_requests"
    __table_args__ = (
        CheckConstraint("status in ('pending','approved','rejected','used')", name="ck_retake_request_status"),
        Index("ix_retake_requests_participant_status", "participant_id", "status"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    participant_id = Column(UUID(as_uuid=False), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    reason = Column(Text, nullable=True)  # peserta: alasan ingin mengerjakan ulang
    status = Column(String(10), nullable=False, default="pending")
    admin_note = Column(Text, nullable=True)
    decided_by = Column(UUID(as_uuid=False), ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    participant = relationship("Participant")
    admin = relationship("Admin")
