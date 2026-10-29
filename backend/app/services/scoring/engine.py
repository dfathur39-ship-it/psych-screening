"""
Scoring Engine
--------------
Semua perhitungan skor dan penentuan kategori hasil dilakukan di sini,
berbasis data dari PostgreSQL (answer_options.score, result_categories.min/max_score).
TIDAK ADA angka hardcode untuk scoring atau kategori.
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.models import ScreeningSession, ScreeningAnswer, ResultCategory, SessionStatus


class ScoringEngine:
    def __init__(self, db: Session):
        self.db = db

    def compute_total_score(self, session_id: str) -> int:
        answers = (
            self.db.query(ScreeningAnswer)
            .filter(ScreeningAnswer.screening_session_id == session_id)
            .all()
        )
        return sum(a.score for a in answers)

    def resolve_category(self, total_score: int) -> Optional[ResultCategory]:
        """
        Cari kategori aktif dimana min_score <= total_score <= max_score.
        Jika ada overlap range (data tidak konsisten), pilih kategori dengan
        rentang paling sempit (paling spesifik) secara deterministik, bukan random,
        agar hasil tidak ambigu.
        Jika tidak ada kategori cocok, return None (caller harus menangani).
        """
        candidates = (
            self.db.query(ResultCategory)
            .filter(
                ResultCategory.active.is_(True),
                ResultCategory.min_score <= total_score,
                ResultCategory.max_score >= total_score,
            )
            .all()
        )
        if not candidates:
            return None
        candidates.sort(key=lambda c: (c.max_score - c.min_score, c.min_score))
        return candidates[0]

    def finalize_session(self, session: ScreeningSession) -> ScreeningSession:
        total = self.compute_total_score(session.id)
        category = self.resolve_category(total)
        session.total_score = total
        session.result_category_id = category.id if category else None
        session.status = SessionStatus.completed
        from sqlalchemy.sql import func
        session.completed_at = func.now()
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
