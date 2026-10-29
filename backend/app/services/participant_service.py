"""Helper bersama untuk membentuk respons peserta (status KTP, NIK tersamar, sesi skrining)."""
import uuid

from sqlalchemy.orm import Session

from app.models.models import Participant, RetakeRequest, ScreeningSession, SessionStatus
from app.schemas.schemas import ParticipantOut, ParticipantProfileOut
from app.utils.privacy import mask_nik


def is_ktp_confirmed(participant: Participant) -> bool:
    """KTP dianggap terkonfirmasi setelah peserta memeriksa datanya (NIK tersimpan dan dokumen ditandai dikoreksi)."""
    doc = participant.ktp_document
    return bool(participant.nik and doc is not None and doc.corrected_by_user)


def to_participant_out(participant: Participant) -> ParticipantOut:
    out = ParticipantOut.model_validate(participant)
    out.nik_masked = mask_nik(participant.nik)
    out.ktp_confirmed = is_ktp_confirmed(participant)
    return out


def get_latest_retake_request(db: Session, participant_id: str) -> RetakeRequest | None:
    return (
        db.query(RetakeRequest)
        .filter(RetakeRequest.participant_id == participant_id)
        .order_by(RetakeRequest.created_at.desc())
        .first()
    )


def has_completed_session(db: Session, participant_id: str) -> bool:
    return (
        db.query(ScreeningSession)
        .filter(ScreeningSession.participant_id == participant_id, ScreeningSession.status == SessionStatus.completed)
        .first()
        is not None
    )


def get_unused_approved_retake(db: Session, participant_id: str) -> RetakeRequest | None:
    """An approved request not yet spent on a new session. There is at most one at a time,
    since a new request can't be filed while one is pending or approved."""
    return (
        db.query(RetakeRequest)
        .filter(RetakeRequest.participant_id == participant_id, RetakeRequest.status == "approved")
        .order_by(RetakeRequest.created_at.desc())
        .first()
    )


def to_profile_out(db: Session, participant: Participant) -> ParticipantProfileOut:
    base = to_participant_out(participant).model_dump()
    sessions = (
        db.query(ScreeningSession)
        .filter(ScreeningSession.participant_id == participant.id)
        .order_by(ScreeningSession.created_at.desc())
        .all()
    )
    in_progress = next((s for s in sessions if s.status == SessionStatus.in_progress), None)
    completed = next((s for s in sessions if s.status == SessionStatus.completed), None)

    latest_retake = get_latest_retake_request(db, participant.id)
    retake_status = latest_retake.status if latest_retake and latest_retake.status != "used" else None

    return ParticipantProfileOut(
        **base,
        in_progress_session_id=in_progress.id if in_progress else None,
        completed_session_id=completed.id if completed else None,
        retake_status=retake_status,
    )


def is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False
