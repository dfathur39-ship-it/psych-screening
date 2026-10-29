from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import require_role
from app.models.models import AuditLog, Admin, AdminRole
from app.schemas.schemas import PaginatedResponse

router = APIRouter(prefix="/api/admin/audit-logs", tags=["admin-audit"])


@router.get("", response_model=PaginatedResponse)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_role(AdminRole.superadmin, AdminRole.admin)),
):
    query = db.query(AuditLog).options(joinedload(AuditLog.admin))
    total = query.count()
    items = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    result_items = [{
        "id": a.id,
        "admin_username": a.admin.username if a.admin else "system",
        "action": a.action,
        "target_type": a.target_type,
        "target_id": a.target_id,
        "description": a.description,
        "ip_address": a.ip_address,
        "created_at": a.created_at.isoformat(),
    } for a in items]
    return PaginatedResponse(
        items=result_items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
