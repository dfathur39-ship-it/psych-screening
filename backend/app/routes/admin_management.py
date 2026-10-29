from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.core.errors import conflict, not_found, bad_request
from app.core.security import hash_password
from app.models.models import Admin, AdminRole
from app.schemas.schemas import AdminCreate, AdminOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/admin/admins", tags=["admin-management"])


@router.get("", response_model=list[AdminOut])
def list_admins(db: Session = Depends(get_db), admin: Admin = Depends(require_role(AdminRole.superadmin))):
    return db.query(Admin).all()


@router.post("", response_model=AdminOut, status_code=201)
def create_admin(payload: AdminCreate, request: Request, db: Session = Depends(get_db),
                  admin: Admin = Depends(require_role(AdminRole.superadmin))):
    existing = db.query(Admin).filter(Admin.username == payload.username).first()
    if existing:
        raise conflict("Username sudah digunakan", "USERNAME_ALREADY_EXISTS")
    try:
        role = AdminRole(payload.role)
    except ValueError:
        raise bad_request("Role tidak valid", "INVALID_ROLE")

    new_admin = Admin(username=payload.username, password_hash=hash_password(payload.password), role=role)
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    log_action(db, admin.id, "CREATE_ADMIN", "admin", new_admin.id, f"Membuat admin {payload.username}",
               request.client.host if request.client else None)
    return new_admin


@router.put("/{admin_id}/deactivate")
def deactivate_admin(admin_id: str, request: Request, db: Session = Depends(get_db),
                      admin: Admin = Depends(require_role(AdminRole.superadmin))):
    target = db.query(Admin).filter(Admin.id == admin_id).first()
    if not target:
        raise not_found("Admin tidak ditemukan", "ADMIN_NOT_FOUND")
    target.active = False
    db.commit()
    log_action(db, admin.id, "DEACTIVATE_ADMIN", "admin", admin_id, "Menonaktifkan admin",
               request.client.host if request.client else None)
    return {"success": True, "message": "Admin dinonaktifkan"}
