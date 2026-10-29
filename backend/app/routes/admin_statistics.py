from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.models.models import Participant, ScreeningSession, Position, Question, ResultCategory, Admin, SessionStatus

router = APIRouter(prefix="/api/admin/statistics", tags=["admin-statistics"])


@router.get("")
def get_statistics(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    total_participants = db.query(func.count(Participant.id)).scalar()
    total_screenings = db.query(func.count(ScreeningSession.id)).scalar()
    total_positions = db.query(func.count(Position.id)).scalar()
    total_questions = db.query(func.count(Question.id)).scalar()

    by_category = (
        db.query(ResultCategory.name, func.count(ScreeningSession.id))
        .join(ScreeningSession, ScreeningSession.result_category_id == ResultCategory.id)
        .filter(ScreeningSession.status == SessionStatus.completed)
        .group_by(ResultCategory.name)
        .all()
    )
    by_jabatan = (
        db.query(Position.nama_jabatan, func.count(ScreeningSession.id))
        .join(ScreeningSession, ScreeningSession.position_id == Position.id)
        .group_by(Position.nama_jabatan)
        .all()
    )

    return {
        "total_participants": total_participants,
        "total_screenings": total_screenings,
        "total_positions": total_positions,
        "total_questions": total_questions,
        "distribusi_kategori": [{"label": n, "value": c} for n, c in by_category],
        "distribusi_jabatan": [{"label": n, "value": c} for n, c in by_jabatan],
    }
