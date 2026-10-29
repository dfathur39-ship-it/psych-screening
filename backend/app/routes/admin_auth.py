from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import unauthorized
from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_admin
from app.models.models import Admin
from app.schemas.schemas import AdminLogin, AdminTokenOut, AdminOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/admin", tags=["admin-auth"])


@router.post("/login", response_model=AdminTokenOut)
def admin_login(payload: AdminLogin, request: Request, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == payload.username).first()
    if not admin or not admin.active or not verify_password(payload.password, admin.password_hash):
        raise unauthorized("Username atau password salah", "INVALID_CREDENTIALS")

    token = create_access_token({"admin_id": admin.id, "role": admin.role.value})
    log_action(db, admin.id, "LOGIN", "admin", admin.id, "Admin login",
               request.client.host if request.client else None)
    return AdminTokenOut(access_token=token, role=admin.role.value, username=admin.username)


@router.get("/me", response_model=AdminOut)
def get_me(admin: Admin = Depends(get_current_admin)):
    return admin


@router.post("/logout")
def admin_logout(admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    # Stateless JWT: logout is enforced client-side by discarding the token.
    # Server-side, we record the action for audit purposes.
    log_action(db, admin.id, "LOGOUT", "admin", admin.id, "Admin logout")
    return {"success": True, "message": "Logout berhasil"}
