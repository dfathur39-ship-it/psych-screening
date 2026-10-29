from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.core.errors import not_found, conflict
from app.models.models import Position, PositionQuestion, Admin
from app.schemas.schemas import PositionCreate, PositionUpdate, PositionOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/admin/positions", tags=["admin-positions"])


@router.get("", response_model=list[PositionOut])
def list_positions(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    positions = db.query(Position).all()
    result = []
    for p in positions:
        count = db.query(func.count(PositionQuestion.id)).filter(PositionQuestion.position_id == p.id).scalar()
        out = PositionOut.model_validate(p)
        out.question_count = count
        result.append(out)
    return result


@router.post("", response_model=PositionOut, status_code=201)
def create_position(payload: PositionCreate, request: Request, db: Session = Depends(get_db),
                     admin: Admin = Depends(get_current_admin)):
    existing = db.query(Position).filter(Position.nama_jabatan.ilike(payload.nama_jabatan.strip())).first()
    if existing:
        raise conflict("Jabatan dengan nama tersebut sudah ada", "POSITION_ALREADY_EXISTS")
    position = Position(nama_jabatan=payload.nama_jabatan.strip(), description=payload.description,
                         active=payload.active)
    db.add(position)
    db.commit()
    db.refresh(position)
    log_action(db, admin.id, "CREATE_POSITION", "position", position.id, "Membuat jabatan baru",
               request.client.host if request.client else None)
    out = PositionOut.model_validate(position)
    out.question_count = 0
    return out


@router.put("/{position_id}", response_model=PositionOut)
def update_position(position_id: str, payload: PositionUpdate, request: Request,
                     db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise not_found("Jabatan tidak ditemukan", "POSITION_NOT_FOUND")
    if payload.nama_jabatan is not None:
        position.nama_jabatan = payload.nama_jabatan.strip()
    if payload.description is not None:
        position.description = payload.description
    if payload.active is not None:
        position.active = payload.active
    db.commit()
    db.refresh(position)
    log_action(db, admin.id, "UPDATE_POSITION", "position", position.id, "Mengubah jabatan",
               request.client.host if request.client else None)
    count = db.query(func.count(PositionQuestion.id)).filter(PositionQuestion.position_id == position.id).scalar()
    out = PositionOut.model_validate(position)
    out.question_count = count
    return out


@router.delete("/{position_id}")
def delete_position(position_id: str, request: Request, db: Session = Depends(get_db),
                     admin: Admin = Depends(get_current_admin)):
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise not_found("Jabatan tidak ditemukan", "POSITION_NOT_FOUND")
    db.delete(position)
    db.commit()
    log_action(db, admin.id, "DELETE_POSITION", "position", position_id, "Menghapus jabatan",
               request.client.host if request.client else None)
    return {"success": True, "message": "Jabatan dihapus"}
