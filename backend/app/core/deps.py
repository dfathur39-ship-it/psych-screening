from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import Admin, AdminRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Token tidak ditemukan", "error_code": "UNAUTHORIZED"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload or "admin_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Token tidak valid atau kedaluwarsa", "error_code": "INVALID_TOKEN"},
        )
    admin = db.query(Admin).filter(Admin.id == payload["admin_id"], Admin.active.is_(True)).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Admin tidak ditemukan atau nonaktif", "error_code": "ADMIN_NOT_FOUND"},
        )
    return admin


def require_role(*roles: AdminRole):
    def checker(admin: Admin = Depends(get_current_admin)) -> Admin:
        if admin.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "message": "Tidak memiliki izin akses", "error_code": "FORBIDDEN"},
            )
        return admin
    return checker
