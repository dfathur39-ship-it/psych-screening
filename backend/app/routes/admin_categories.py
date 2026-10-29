from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.core.errors import not_found
from app.models.models import ResultCategory, Admin
from app.schemas.schemas import ResultCategoryCreate, ResultCategoryUpdate, ResultCategoryOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/admin/categories", tags=["admin-categories"])


@router.get("", response_model=list[ResultCategoryOut])
def list_categories(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    return db.query(ResultCategory).order_by(ResultCategory.min_score.asc()).all()


@router.post("", response_model=ResultCategoryOut, status_code=201)
def create_category(payload: ResultCategoryCreate, request: Request, db: Session = Depends(get_db),
                     admin: Admin = Depends(get_current_admin)):
    category = ResultCategory(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    log_action(db, admin.id, "CREATE_CATEGORY", "result_category", category.id,
               "Membuat kategori hasil baru", request.client.host if request.client else None)
    return category


@router.put("/{category_id}", response_model=ResultCategoryOut)
def update_category(category_id: str, payload: ResultCategoryUpdate, request: Request,
                     db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    category = db.query(ResultCategory).filter(ResultCategory.id == category_id).first()
    if not category:
        raise not_found("Kategori tidak ditemukan", "CATEGORY_NOT_FOUND")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(category, key, value)
    if category.min_score > category.max_score:
        from app.core.errors import bad_request
        raise bad_request("min_score tidak boleh lebih besar dari max_score", "INVALID_SCORE_RANGE")
    db.commit()
    db.refresh(category)
    log_action(db, admin.id, "UPDATE_CATEGORY", "result_category", category.id,
               "Mengubah kategori hasil", request.client.host if request.client else None)
    return category


@router.delete("/{category_id}")
def delete_category(category_id: str, request: Request, db: Session = Depends(get_db),
                     admin: Admin = Depends(get_current_admin)):
    category = db.query(ResultCategory).filter(ResultCategory.id == category_id).first()
    if not category:
        raise not_found("Kategori tidak ditemukan", "CATEGORY_NOT_FOUND")
    db.delete(category)
    db.commit()
    log_action(db, admin.id, "DELETE_CATEGORY", "result_category", category_id,
               "Menghapus kategori hasil", request.client.host if request.client else None)
    return {"success": True, "message": "Kategori dihapus"}
