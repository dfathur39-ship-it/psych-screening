"""
Resolusi jabatan bebas-teks ke entitas Position di database.

Kebijakan (modular, dapat dikonfigurasi admin di masa depan):
1. Cari Position dengan nama_jabatan yang cocok (case-insensitive, trimmed).
2. Jika tidak ditemukan, buat Position baru (active=True) agar admin dapat
   memetakan pertanyaan untuknya di kemudian hari. User tetap dapat melanjutkan.
3. Untuk daftar pertanyaan sesi ini:
   - Jika position memiliki mapping pertanyaan aktif -> gunakan itu.
   - Jika tidak ada mapping (posisi baru / belum dikonfigurasi admin) -> fallback
     ke seluruh pertanyaan aktif yang tidak terikat jabatan manapun, sebagai
     general screening. Ini mencegah user terhenti di tengah proses.
"""
from sqlalchemy.orm import Session

from app.models.models import Position, Question, PositionQuestion


def resolve_position(db: Session, jabatan_text: str) -> Position:
    jabatan_clean = jabatan_text.strip()
    position = (
        db.query(Position)
        .filter(Position.nama_jabatan.ilike(jabatan_clean))
        .first()
    )
    if position:
        return position

    position = Position(nama_jabatan=jabatan_clean, active=True,
                         description="Dibuat otomatis dari input peserta; belum dipetakan pertanyaan oleh admin.")
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


def get_questions_for_position(db: Session, position: Position) -> list[Question]:
    mapped = (
        db.query(Question)
        .join(PositionQuestion, PositionQuestion.question_id == Question.id)
        .filter(PositionQuestion.position_id == position.id, Question.active.is_(True))
        .order_by(PositionQuestion.order_number.asc())
        .all()
    )
    if mapped:
        return mapped

    # Fallback: no questions have been mapped to this position yet (e.g. a brand
    # new position auto-created from free-text jabatan input, or an existing
    # position an admin hasn't configured yet). Rather than leaving the user
    # stuck with an empty screening, fall back to ALL active questions so they
    # can still complete a general screening. Admins can later map specific
    # questions to this position via the Positions/Questions admin screens.
    fallback = db.query(Question).filter(Question.active.is_(True)).all()
    return fallback
