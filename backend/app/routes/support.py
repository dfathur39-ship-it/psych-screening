"""Public help/contact chat. Visitors have no account; a random per-thread secret
token (sent in the X-Thread-Token header) authorises access to their own thread only."""
import hashlib
import hmac
import secrets
import uuid

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.database import get_db
from app.core.errors import conflict, not_found
from app.services.participant_service import is_valid_uuid
from app.core.limiter import limiter
from app.models.models import Participant, SupportThread, SupportMessage
from app.schemas.schemas import SupportThreadCreate, SupportMessageCreate, SupportMessageOut

router = APIRouter(prefix="/api/support", tags=["support"])

MAX_MESSAGES_RETURNED = 200


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_visitor_thread(
    thread_id: str,
    x_thread_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> SupportThread:
    # Same 404 for "no such thread" and "wrong token" so thread ids can't be probed (IDOR).
    err = not_found("Percakapan tidak ditemukan", "THREAD_NOT_FOUND")
    if not x_thread_token:
        raise err
    try:
        uuid.UUID(thread_id)
    except ValueError:
        raise err
    thread = db.query(SupportThread).filter(SupportThread.id == thread_id).first()
    if not thread or not hmac.compare_digest(thread.token_hash, hash_token(x_thread_token)):
        raise err
    return thread


def _serialize(thread: SupportThread, messages: list[SupportMessage]) -> dict:
    return {
        "thread_id": thread.id,
        "status": thread.status,
        "messages": [SupportMessageOut.model_validate(m).model_dump(mode="json") for m in messages],
    }


def _recent_messages(db: Session, thread_id: str) -> list[SupportMessage]:
    rows = (
        db.query(SupportMessage)
        .filter(SupportMessage.thread_id == thread_id)
        .order_by(SupportMessage.created_at.desc())
        .limit(MAX_MESSAGES_RETURNED)
        .all()
    )
    return list(reversed(rows))


@router.post("/threads", status_code=201)
@limiter.limit("5/minute")
def create_thread(request: Request, payload: SupportThreadCreate, db: Session = Depends(get_db)):
    # "Login" lewat data diri: nama dan kontak diambil dari peserta, bukan diketik ulang.
    participant = (
        db.query(Participant).filter(Participant.id == payload.participant_id).first()
        if is_valid_uuid(payload.participant_id) else None
    )
    if not participant:
        raise not_found("Data diri tidak ditemukan. Isi data diri terlebih dahulu.", "PARTICIPANT_NOT_FOUND")

    contact = " / ".join(x for x in (participant.email, participant.no_hp) if x)[:150] or None
    token = secrets.token_urlsafe(32)
    thread = SupportThread(visitor_name=participant.nama[:100], visitor_contact=contact,
                            token_hash=hash_token(token))
    db.add(thread)
    db.flush()
    db.add(SupportMessage(thread_id=thread.id, sender="visitor", body=payload.message))
    db.commit()
    db.refresh(thread)
    return {"thread_id": thread.id, "token": token, **_serialize(thread, _recent_messages(db, thread.id))}


@router.get("/threads/{thread_id}/messages")
def list_messages(thread: SupportThread = Depends(get_visitor_thread), db: Session = Depends(get_db)):
    return _serialize(thread, _recent_messages(db, thread.id))


@router.post("/threads/{thread_id}/messages", status_code=201)
@limiter.limit("30/minute")
def send_message(request: Request, payload: SupportMessageCreate,
                  thread: SupportThread = Depends(get_visitor_thread), db: Session = Depends(get_db)):
    # Once admin marks a conversation done, the visitor can't keep chatting in it:
    # they have to start a new conversation.
    if thread.status == "closed":
        raise conflict(
            "Percakapan ini sudah diselesaikan admin. Mulai percakapan baru untuk chat lagi.",
            "THREAD_CLOSED",
        )
    db.add(SupportMessage(thread_id=thread.id, sender="visitor", body=payload.body))
    thread.last_message_at = func.now()
    db.commit()
    db.refresh(thread)
    return _serialize(thread, _recent_messages(db, thread.id))
