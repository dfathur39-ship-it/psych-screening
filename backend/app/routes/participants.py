from fastapi import APIRouter, Depends, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import bad_request, conflict, not_found
from app.models.models import Participant, RetakeRequest
from app.schemas.schemas import (
    ParticipantCreate, ParticipantOut, ParticipantProfileOut, RetakeRequestCreate, RetakeRequestOut,
)
from app.services.identity_service import clean_spaces, find_by_name, match_existing_account
from app.services.participant_service import (
    get_latest_retake_request, has_completed_session, is_valid_uuid, to_participant_out, to_profile_out,
)

router = APIRouter(prefix="/api/participants", tags=["participants"])


@router.post("", response_model=ParticipantOut, status_code=201)
def create_participant(payload: ParticipantCreate, response: Response, db: Session = Depends(get_db)):
    """Daftar atau masuk. Data diri yang persis sama dengan akun yang sudah ada masuk ke akun itu (200).
    Nama yang sama dengan data yang berbeda ditolak (409), jadi satu orang tidak bisa punya dua akun."""
    nama = clean_spaces(payload.nama)
    jabatan = clean_spaces(payload.jabatan)
    existing = find_by_name(db, nama)
    if existing:
        if not match_existing_account(existing, email=payload.email, no_hp=payload.no_hp,
                                      usia=payload.usia, jabatan=jabatan):
            raise conflict(
                "Nama ini sudah terdaftar dengan data yang berbeda. Isi data yang sama persis seperti saat "
                "pertama mendaftar (email, nomor HP, usia, dan jabatan), atau hubungi admin.",
                "NAMA_SUDAH_TERDAFTAR",
            )
        response.status_code = 200
        return to_participant_out(existing)

    participant = Participant(
        nama=nama,
        usia=payload.usia,
        jabatan=jabatan,
        no_hp=payload.no_hp.strip(),
        email=payload.email,
    )
    db.add(participant)
    try:
        db.commit()
    except IntegrityError:
        # Dua permintaan bersamaan dengan nama yang sama: yang kedua kalah.
        db.rollback()
        raise conflict("Nama ini sudah terdaftar. Coba masuk lagi dengan data yang sama.", "NAMA_SUDAH_TERDAFTAR") from None
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
            else "Permintaanmu sudah disetujui, silakan mulai skrining dari beranda"
        )
        raise conflict(message, "RETAKE_REQUEST_EXISTS")

    request = RetakeRequest(participant_id=participant_id, reason=payload.reason, status="pending")
    db.add(request)
    db.commit()
    db.refresh(request)
    return request
