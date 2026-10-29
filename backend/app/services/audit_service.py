from sqlalchemy.orm import Session
from app.models.models import AuditLog


def log_action(db: Session, admin_id: str | None, action: str, target_type: str = None,
                target_id: str = None, description: str = None, ip_address: str = None):
    entry = AuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        description=description,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
