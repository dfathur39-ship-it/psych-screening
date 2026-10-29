"""Admin review of participants' requests to redo a completed screening."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.core.errors import conflict, not_found
from app.models.models import Admin, Participant, RetakeRequest
from app.schemas.schemas import AdminRetakeRequestOut, PaginatedResponse, RetakeDecision
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/admin/retake-requests", tags=["admin-retake"])


def _serialize(r: RetakeRequest) -> dict:
    p = r.participant
    return {
        "id": r.id,
        "participant_id": r.participant_id,
        "participant_nama": p.nama if p else "-",
        "participant_jabatan": p.jabatan if p else "-",
        "participant_no_hp": p.no_hp if p else "-",
        "participant_email": p.email if p else None,
        "reason": r.reason,
        "status": r.status,
        "admin_note": r.admin_note,
        "created_at": r.created_at,
        "decided_at": r.decided_at,
    }


@router.get("/pending-count")
def pending_count(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    return {"pending": db.query(RetakeRequest).filter(RetakeRequest.status == "pending").count()}


@router.get("", response_model=PaginatedResponse)
def list_retake_requests(
    status: str = Query("pending", pattern="^(all|pending|approved|rejected|used)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    query = db.query(RetakeRequest).join(Participant, RetakeRequest.participant_id == Participant.id)
    if status != "all":
        query = query.filter(RetakeRequest.status == status)
    total = query.count()
    rows = (
        query.order_by(RetakeRequest.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    return PaginatedResponse(
        items=[_serialize(r) for r in rows], total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("/{request_id}/decision", response_model=AdminRetakeRequestOut)
def decide_retake_request(request_id: str, payload: RetakeDecision, db: Session = Depends(get_db),
                           admin: Admin = Depends(get_current_admin)):
    req = db.query(RetakeRequest).filter(RetakeRequest.id == request_id).first()
    if not req:
        raise not_found("Permintaan tidak ditemukan", "RETAKE_REQUEST_NOT_FOUND")
    if req.status != "pending":
        raise conflict(f"Permintaan ini sudah diputuskan sebelumnya ({req.status})", "RETAKE_ALREADY_DECIDED")

    req.status = payload.status
    req.admin_note = payload.admin_note
    req.decided_by = admin.id
    req.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(req)

    log_action(db, admin.id, "RETAKE_REQUEST_" + payload.status.upper(), "retake_request", req.id,
               f"Peserta: {req.participant.nama if req.participant else req.participant_id}")
    return _serialize(req)
