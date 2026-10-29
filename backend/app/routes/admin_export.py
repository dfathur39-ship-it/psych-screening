import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from openpyxl import Workbook

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.models.models import ScreeningSession, Admin, SessionStatus
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/admin/export", tags=["admin-export"])

HEADERS = ["Tanggal", "Nama", "Usia", "Jabatan", "Score", "Kategori"]


def _get_rows(db: Session):
    sessions = (
        db.query(ScreeningSession)
        .options(joinedload(ScreeningSession.participant), joinedload(ScreeningSession.result_category))
        .filter(ScreeningSession.status == SessionStatus.completed)
        .order_by(ScreeningSession.completed_at.desc())
        .all()
    )
    rows = []
    for s in sessions:
        p = s.participant
        rows.append([
            s.completed_at.strftime("%Y-%m-%d %H:%M") if s.completed_at else "",
            p.nama if p else "",
            p.usia if p else "",
            p.jabatan if p else "",
            s.total_score,
            s.result_category.name if s.result_category else "",
        ])
    # NOTE: NIK is intentionally excluded from export by default per privacy policy.
    return rows


@router.get("/csv")
def export_csv(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    rows = _get_rows(db)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADERS)
    writer.writerows(rows)
    buffer.seek(0)
    log_action(db, admin.id, "EXPORT_CSV", "screening_sessions", None, f"Export {len(rows)} baris ke CSV")
    filename = f"skrining_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/excel")
def export_excel(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    rows = _get_rows(db)
    wb = Workbook()
    ws = wb.active
    ws.title = "Hasil Skrining"
    ws.append(HEADERS)
    for row in rows:
        ws.append(row)

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    log_action(db, admin.id, "EXPORT_EXCEL", "screening_sessions", None, f"Export {len(rows)} baris ke Excel")
    filename = f"skrining_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
