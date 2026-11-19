import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from openpyxl import Workbook

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.models.models import ScreeningSession, Admin, SessionStatus
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/admin/export", tags=["admin-export"])

HEADERS = ["No", "Nama", "Usia", "Jabatan", "Email", "No HP", "Mulai", "Selesai", "Durasi", "Score", "Kategori"]
WIB = ZoneInfo("Asia/Jakarta")


def _fmt(dt):
    """Waktu dalam WIB, format tanggal-bulan-tahun jam:menit."""
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(WIB).strftime("%d-%m-%Y %H:%M")


def _duration(start, end):
    if not start or not end:
        return ""
    secs = int((end - start).total_seconds())
    if secs < 0:
        return ""
    h, rem = divmod(secs, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h} jam {m} mnt"
    return f"{m} mnt {sec} dtk"


def _get_rows(db: Session):
    sessions = (
        db.query(ScreeningSession)
        .options(joinedload(ScreeningSession.participant), joinedload(ScreeningSession.result_category))
        .filter(ScreeningSession.status == SessionStatus.completed)
        .order_by(ScreeningSession.completed_at.desc())
        .all()
    )
    rows = []
    for i, s in enumerate(sessions, 1):
        p = s.participant
        rows.append([
            i,
            p.nama if p else "",
            p.usia if p else "",
            p.jabatan if p else "",
            (p.email or "") if p else "",
            p.no_hp if p else "",
            _fmt(s.started_at),
            _fmt(s.completed_at),
            _duration(s.started_at, s.completed_at),
            s.total_score,
            s.result_category.name if s.result_category else "",
        ])
    # NOTE: NIK sengaja tidak diekspor (kebijakan privasi).
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


@router.get("/pdf")
def export_pdf(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    rows = _get_rows(db)
    stream = io.BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=landscape(A4), leftMargin=1 * cm, rightMargin=1 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm, title="Hasil Skrining Psikologi")
    styles = getSampleStyleSheet()
    cell = styles["BodyText"]
    cell.fontSize = 7.5
    cell.leading = 9
    header = [Paragraph(f"<b>{h}</b>", cell) for h in HEADERS]
    body = [[Paragraph(str(c), cell) for c in r] for r in rows] or [[Paragraph("Belum ada data", cell)] + [""] * (len(HEADERS) - 1)]
    widths = [0.9, 3.6, 1.1, 3.0, 4.0, 2.4, 2.6, 2.6, 2.0, 1.2, 2.6]
    table = Table([header] + body, colWidths=[w * cm for w in widths], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E3EEE8")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C4BD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9F8")]),
    ]))
    stamp = datetime.now(WIB).strftime("%d-%m-%Y %H:%M")
    doc.build([
        Paragraph("Hasil Skrining Psikologi", styles["Title"]),
        Paragraph(f"Dibuat {stamp} WIB. Total {len(rows)} peserta selesai.", styles["Normal"]),
        Spacer(1, 0.4 * cm),
        table,
    ])
    stream.seek(0)
    log_action(db, admin.id, "EXPORT_PDF", "screening_sessions", None, f"Export {len(rows)} baris ke PDF")
    filename = f"skrining_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(stream, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})
