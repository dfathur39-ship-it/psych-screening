from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import unauthorized, bad_request, conflict
from app.core.security import verify_password, create_access_token, hash_password
from app.core.deps import get_current_admin
from app.models.models import Admin
from app.schemas.schemas import AdminLogin, AdminTokenOut, AdminOut, AdminProfileUpdate
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


@router.put("/me/profile", response_model=AdminTokenOut)
def update_my_profile(payload: AdminProfileUpdate, request: Request,
                      admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Admin mengganti username dan/atau password miliknya sendiri (wajib password saat ini)."""
    if not verify_password(payload.current_password, admin.password_hash):
        # 400, bukan 401: klien menganggap 401 sebagai sesi habis dan akan logout otomatis.
        raise bad_request("Password saat ini salah", "INVALID_CURRENT_PASSWORD")
    if not payload.new_username and not payload.new_password:
        raise bad_request("Isi username baru atau password baru", "NOTHING_TO_UPDATE")

    changed = []
    if payload.new_username and payload.new_username != admin.username:
        taken = db.query(Admin).filter(Admin.username == payload.new_username, Admin.id != admin.id).first()
        if taken:
            raise conflict("Username sudah dipakai", "USERNAME_TAKEN")
        admin.username = payload.new_username
        changed.append("username")
    if payload.new_password:
        if verify_password(payload.new_password, admin.password_hash):
            raise bad_request("Password baru tidak boleh sama dengan password saat ini", "PASSWORD_UNCHANGED")
        admin.password_hash = hash_password(payload.new_password)
        changed.append("password")
    if not changed:
        raise bad_request("Tidak ada yang berubah", "NOTHING_TO_UPDATE")

    db.commit()
    # Catat perubahan tanpa menyimpan nilai password/username lama maupun baru.
    log_action(db, admin.id, "PROFILE_UPDATE", "admin", admin.id, "Admin mengubah " + " dan ".join(changed),
               request.client.host if request.client else None)
    token = create_access_token({"admin_id": admin.id, "role": admin.role.value})
    return AdminTokenOut(access_token=token, role=admin.role.value, username=admin.username)


@router.post("/logout")
def admin_logout(admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    # Stateless JWT: logout is enforced client-side by discarding the token.
    # Server-side, we record the action for audit purposes.
    log_action(db, admin.id, "LOGOUT", "admin", admin.id, "Admin logout")
    return {"success": True, "message": "Logout berhasil"}
