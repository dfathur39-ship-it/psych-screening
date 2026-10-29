from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.models.models import Participant, ScreeningSession, Admin, SessionStatus
from app.schemas.schemas import PaginatedResponse
from app.utils.privacy import mask_nik

router = APIRouter(prefix="/api/admin", tags=["admin-data"])


@router.get("/participants", response_model=PaginatedResponse)
def list_participants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    jabatan: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    query = db.query(Participant)
    if search:
        query = query.filter(or_(Participant.nama.ilike(f"%{search}%"), Participant.no_hp.ilike(f"%{search}%"),
                                     Participant.email.ilike(f"%{search}%")))
    if jabatan:
        query = query.filter(Participant.jabatan.ilike(f"%{jabatan}%"))
    if date_from:
        query = query.filter(Participant.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Participant.created_at <= datetime.fromisoformat(date_to))

    total = query.count()
    items = (
        query.order_by(Participant.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    result_items = []
    for p in items:
        result_items.append({
            "id": p.id, "nama": p.nama, "usia": p.usia,
            "jabatan": p.jabatan, "no_hp": p.no_hp, "email": p.email, "nik_masked": mask_nik(p.nik),
            "created_at": p.created_at.isoformat(),
        })
    return PaginatedResponse(
        items=result_items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/participants/{participant_id}")
def get_participant_detail(participant_id: str, db: Session = Depends(get_db),
                            admin: Admin = Depends(get_current_admin)):
    from app.core.errors import not_found
    p = db.query(Participant).options(joinedload(Participant.screening_sessions)).filter(
        Participant.id == participant_id).first()
    if not p:
        raise not_found("Peserta tidak ditemukan", "PARTICIPANT_NOT_FOUND")
    return {
        "id": p.id, "nama": p.nama, "usia": p.usia, "jabatan": p.jabatan,
        "no_hp": p.no_hp, "email": p.email, "nik_masked": mask_nik(p.nik),
        "created_at": p.created_at.isoformat(),
        "screenings": [
            {
                "id": s.id, "total_score": s.total_score, "status": s.status.value,
                "category": s.result_category.name if s.result_category else None,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            } for s in p.screening_sessions
        ],
    }


@router.get("/screenings", response_model=PaginatedResponse)
def list_screenings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    category_id: str | None = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    query = db.query(ScreeningSession).options(
        joinedload(ScreeningSession.participant),
        joinedload(ScreeningSession.result_category),
        joinedload(ScreeningSession.position),
    )
    if status_filter:
        query = query.filter(ScreeningSession.status == SessionStatus(status_filter))
    if category_id:
        query = query.filter(ScreeningSession.result_category_id == category_id)

    total = query.count()
    items = (
        query.order_by(ScreeningSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    result_items = [{
        "id": s.id,
        "participant_nama": s.participant.nama if s.participant else None,
        "jabatan": s.position.nama_jabatan if s.position else None,
        "total_score": s.total_score,
        "category": s.result_category.name if s.result_category else None,
        "status": s.status.value,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    } for s in items]
    return PaginatedResponse(
        items=result_items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
