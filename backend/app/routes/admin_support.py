import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.core.errors import not_found
from app.models.models import Admin, SupportThread, SupportMessage
from app.schemas.schemas import (
    PaginatedResponse, SupportMessageCreate, SupportMessageOut, SupportStatusUpdate,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/admin/support", tags=["admin-support"])


def _get_thread(db: Session, thread_id: str) -> SupportThread:
    try:
        uuid.UUID(thread_id)
    except ValueError:
        raise not_found("Percakapan tidak ditemukan", "THREAD_NOT_FOUND")
    thread = db.query(SupportThread).filter(SupportThread.id == thread_id).first()
    if not thread:
        raise not_found("Percakapan tidak ditemukan", "THREAD_NOT_FOUND")
    return thread


def _messages(db: Session, thread_id: str) -> list[dict]:
    rows = (
        db.query(SupportMessage)
        .filter(SupportMessage.thread_id == thread_id)
        .order_by(SupportMessage.created_at.asc())
        .all()
    )
    return [SupportMessageOut.model_validate(m).model_dump(mode="json") for m in rows]


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    q = db.query(SupportMessage).filter(SupportMessage.sender == "visitor", SupportMessage.read_at.is_(None))
    return {
        "unread_messages": q.count(),
        "unread_threads": q.with_entities(func.count(func.distinct(SupportMessage.thread_id))).scalar() or 0,
    }


@router.get("/threads", response_model=PaginatedResponse)
def list_threads(
    status: str = Query("all", pattern="^(all|open|closed)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    query = db.query(SupportThread)
    if status != "all":
        query = query.filter(SupportThread.status == status)
    total = query.count()
    threads = (
        query.order_by(SupportThread.last_message_at.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    ids = [t.id for t in threads]

    unread = {}
    last = {}
    if ids:
        unread = dict(
            db.query(SupportMessage.thread_id, func.count(SupportMessage.id))
            .filter(SupportMessage.thread_id.in_(ids), SupportMessage.sender == "visitor",
                    SupportMessage.read_at.is_(None))
            .group_by(SupportMessage.thread_id).all()
        )
        last_rows = (
            db.query(SupportMessage)
            .filter(SupportMessage.thread_id.in_(ids))
            .distinct(SupportMessage.thread_id)
            .order_by(SupportMessage.thread_id, SupportMessage.created_at.desc())
            .all()
        )
        last = {m.thread_id: m for m in last_rows}

    items = []
    for t in threads:
        m = last.get(t.id)
        items.append({
            "id": t.id,
            "visitor_name": t.visitor_name,
            "visitor_contact": t.visitor_contact,
            "status": t.status,
            "last_message_at": t.last_message_at.isoformat(),
            "last_message_preview": (m.body[:120] if m else ""),
            "last_sender": m.sender if m else None,
            "unread_count": unread.get(t.id, 0),
        })
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size,
                             total_pages=(total + page_size - 1) // page_size)


@router.get("/threads/{thread_id}")
def get_thread(thread_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    thread = _get_thread(db, thread_id)
    # opening the conversation marks the visitor's messages as read
    db.query(SupportMessage).filter(
        SupportMessage.thread_id == thread.id, SupportMessage.sender == "visitor",
        SupportMessage.read_at.is_(None),
    ).update({"read_at": datetime.now(timezone.utc)}, synchronize_session=False)
    db.commit()
    return {
        "id": thread.id,
        "visitor_name": thread.visitor_name,
        "visitor_contact": thread.visitor_contact,
        "status": thread.status,
        "messages": _messages(db, thread.id),
    }


@router.post("/threads/{thread_id}/messages", status_code=201)
def reply(thread_id: str, payload: SupportMessageCreate, db: Session = Depends(get_db),
           admin: Admin = Depends(get_current_admin)):
    thread = _get_thread(db, thread_id)
    db.add(SupportMessage(thread_id=thread.id, sender="admin", admin_id=admin.id, body=payload.body))
    thread.status = "open"
    thread.last_message_at = func.now()
    db.commit()
    return {"success": True, "messages": _messages(db, thread.id)}


@router.put("/threads/{thread_id}/status")
def set_status(thread_id: str, payload: SupportStatusUpdate, request: Request,
                db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    thread = _get_thread(db, thread_id)
    thread.status = payload.status
    db.commit()
    log_action(db, admin.id, "SUPPORT_THREAD_" + payload.status.upper(), "support_thread", thread.id,
               "Mengubah status percakapan", request.client.host if request.client else None)
    return {"success": True, "status": thread.status}
