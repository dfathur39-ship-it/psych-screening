from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import bad_request, conflict, not_found
from app.models.models import Participant, RetakeRequest
from app.schemas.schemas import (
    ParticipantCreate, ParticipantOut, ParticipantProfileOut, RetakeRequestCreate, RetakeRequestOut,
)
from app.services.participant_service import (
    get_latest_retake_request, has_completed_session, is_valid_uuid, to_participant_out, to_profile_out,
)

router = APIRouter(prefix="/api/participants", tags=["participants"])


@router.post("", response_model=ParticipantOut, status_code=201)
def create_participant(payload: ParticipantCreate, db: Session = Depends(get_db)):
    participant = Participant(
        nama=payload.nama.strip(),
        usia=payload.usia,
        jabatan=payload.jabatan.strip(),
        no_hp=payload.no_hp.strip(),
        email=payload.email,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return to_participant_out(participant)


@router.get("/{participant_id}", response_model=ParticipantProfileOut)
def get_participant(participant_id: str, db: Session = Depends(get_db)):
    """Profil peserta: data diri, status konfirmasi KTP, dan sesi skrining terakhir."""
    participant = (
        db.query(Participant).filter(Participant.id == participant_id).first()
        if is_valid_uuid(participant_id) else None
    )
    if not participant:
        raise not_found("Peserta tidak ditemukan", "PARTICIPANT_NOT_FOUND")
    return to_profile_out(db, participant)


@router.post("/{participant_id}/retake-requests", response_model=RetakeRequestOut, status_code=201)
def request_retake(participant_id: str, payload: RetakeRequestCreate, db: Session = Depends(get_db)):
    """Peserta yang skriningnya sudah selesai mengajukan izin mengerjakan ulang ke admin."""
    participant = (
        db.query(Participant).filter(Participant.id == participant_id).first()
        if is_valid_uuid(participant_id) else None
    )
    if not participant:
        raise not_found("Peserta tidak ditemukan", "PARTICIPANT_NOT_FOUND")

    if not has_completed_session(db, participant_id):
        raise bad_request(
            "Belum ada skrining yang selesai, jadi belum perlu mengajukan pengerjaan ulang",
            "NO_COMPLETED_SCREENING",
        )

    latest = get_latest_retake_request(db, participant_id)
    if latest and latest.status in ("pending", "approved"):
        message = (
            "Permintaan sebelumnya masih menunggu persetujuan admin"
            if latest.status == "pending"
            else "Permintaan Anda sudah disetujui, silakan mulai skrining dari beranda"
        )
        raise conflict(message, "RETAKE_REQUEST_EXISTS")

    request = RetakeRequest(participant_id=participant_id, reason=payload.reason, status="pending")
    db.add(request)
    db.commit()
    db.refresh(request)
    return request
