import os
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.errors import bad_request, not_found
from app.models.models import Participant, KtpDocument
from app.schemas.schemas import KtpOcrResult, KtpConfirm, ParticipantOut
from app.services.ocr_service import run_ocr_on_image
from app.services.identity_service import ensure_ktp_matches_profile, ensure_nik_available
from app.services.participant_service import to_participant_out

router = APIRouter(prefix="/api/ocr", tags=["ocr"])
logger = logging.getLogger("app.ocr")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _safe_filename(participant_id: str, original: str) -> str:
    ext = os.path.splitext(original)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".jpg"
    # never trust user-provided filename; use uuid + validated extension only
    return f"{participant_id}_{uuid.uuid4().hex}{ext}"


@router.get("/providers")
def ocr_providers():
    """Info provider OCR/VLM tanpa membocorkan key — dipakai frontend/admin."""
    from app.services import vlm_service
    configured = vlm_service.is_vlm_configured()
    return {
        "default": settings.OCR_PROVIDER,
        "tesseract_available": True,
        "vlm_configured": configured,
        "vlm_model": settings.VLM_MODEL if configured else None,
        "auto_confirm": settings.VLM_AUTO_CONFIRM,
        "auto_confirm_min_confidence": settings.VLM_AUTO_CONFIRM_MIN_CONFIDENCE,
    }


def _is_complete_for_auto_confirm(extraction) -> tuple[bool, str]:
    """Semua 13 kolom wajib terisi + format valid. Return (ok, reason)."""
    import re
    required = {
        "nik": extraction.nik, "nama": extraction.nama,
        "tempat_lahir": extraction.tempat_lahir, "tanggal_lahir": extraction.tanggal_lahir,
        "jenis_kelamin": extraction.jenis_kelamin, "alamat": extraction.alamat,
        "rt_rw": extraction.rt_rw, "kelurahan": extraction.kelurahan,
        "kecamatan": extraction.kecamatan, "agama": extraction.agama,
        "status_perkawinan": extraction.status_perkawinan,
        "pekerjaan_ktp": extraction.pekerjaan_ktp,
        "kewarganegaraan": extraction.kewarganegaraan,
    }
    missing = [k for k, v in required.items() if not (v and str(v).strip())]
    if missing:
        return False, f"field_kosong:{','.join(missing)}"
    if not re.fullmatch(r"\d{16}", str(extraction.nik).strip()):
        return False, "nik_tidak_valid"
    if len(str(extraction.nama).strip()) < 2:
        return False, "nama_tidak_valid"
    if not re.match(r"^\d{2}[-/]\d{2}[-/]\d{4}$", str(extraction.tanggal_lahir).strip()):
        return False, "tanggal_lahir_tidak_valid"
    if (extraction.confidence or 0) < settings.VLM_AUTO_CONFIRM_MIN_CONFIDENCE:
        return False, f"confidence_rendah:{extraction.confidence}"
    return True, "ok"


@router.post("/ktp", response_model=KtpOcrResult)
async def upload_and_ocr_ktp(
    participant_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    provider: Optional[str] = Query(default=None, pattern="^(tesseract|vlm|auto)$"),
    auto_confirm: Optional[bool] = Query(default=None),
):
    participant = db.query(Participant).filter(Participant.id == participant_id).first()
    if not participant:
        raise not_found("Peserta tidak ditemukan", "PARTICIPANT_NOT_FOUND")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise bad_request("Format file harus JPG, PNG, atau WEBP", "INVALID_FILE_TYPE")

    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise bad_request(f"Ukuran file maksimal {settings.MAX_UPLOAD_SIZE_MB}MB", "FILE_TOO_LARGE")
    if len(contents) == 0:
        raise bad_request("File kosong", "EMPTY_FILE")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = _safe_filename(participant_id, file.filename or "upload.jpg")
    # path is confined to UPLOAD_DIR; filename is server-generated, no path traversal possible
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(contents)

    extraction = run_ocr_on_image(file_path, provider_override=provider)

    # Mode vlm murni tapi gagal / belum dikonfigurasi -> error tegas, jangan fallback diam-diam
    effective_requested = (provider or settings.OCR_PROVIDER or "tesseract").lower()
    if effective_requested == "vlm" and not extraction.raw_text and extraction.confidence == 0:
        # bersihkan file sementara sebelum error
        try:
            os.remove(file_path)
        except OSError:
            pass
        reason = extraction.fallback_reason or "not_configured"
        if reason in ("not_configured", "vlm_not_configured") or "config" in reason.lower():
            raise bad_request(
                "VLM belum dikonfigurasi (VLM_BASE_URL/VLM_API_KEY/VLM_MODEL kosong). "
                "Set env VLM atau pakai OCR_PROVIDER=auto/tesseract.",
                "VLM_NOT_CONFIGURED",
            )
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail={
            "success": False,
            "message": f"VLM gagal memproses gambar ({reason}). Coba lagi atau pakai Tesseract.",
            "error_code": "VLM_FAILED",
        })

    existing = db.query(KtpDocument).filter(KtpDocument.participant_id == participant_id).first()
    if existing:
        db.delete(existing)
        db.flush()

    ktp_doc = KtpDocument(
        participant_id=participant_id,
        file_path=file_path,
        ocr_raw_text=extraction.raw_text,
        ocr_confidence=extraction.confidence,
        ocr_provider=extraction.provider,
        ocr_fallback_used=extraction.fallback_used,
        tempat_lahir=extraction.tempat_lahir,
        tanggal_lahir=extraction.tanggal_lahir,
        jenis_kelamin=extraction.jenis_kelamin,
        alamat=extraction.alamat,
        rt_rw=extraction.rt_rw,
        kelurahan=extraction.kelurahan,
        kecamatan=extraction.kecamatan,
        agama=extraction.agama,
        status_perkawinan=extraction.status_perkawinan,
        pekerjaan_ktp=extraction.pekerjaan_ktp,
        kewarganegaraan=extraction.kewarganegaraan,
    )
    db.add(ktp_doc)

    # apply retention policy: delete file immediately after OCR if configured
    if settings.KTP_RETENTION_DELETE_AFTER_OCR:
        try:
            os.remove(file_path)
            ktp_doc.file_path = None
            ktp_doc.file_deleted = True
        except OSError:
            logger.warning("Gagal menghapus file KTP setelah OCR")

    # Auto-confirm: bila hasil lengkap + valid, langsung sahkan tanpa isi manual.
    # Default ikut settings.VLM_AUTO_CONFIRM; bisa dioverride per-request ?auto_confirm=0/1.
    want_auto = settings.VLM_AUTO_CONFIRM if auto_confirm is None else auto_confirm
    auto_confirmed = False
    if want_auto:
        ok, _reason = _is_complete_for_auto_confirm(extraction)
        if ok:
            try:
                ensure_ktp_matches_profile(participant, nama_ktp=str(extraction.nama),
                                           tanggal_lahir=str(extraction.tanggal_lahir).strip())
                ensure_nik_available(db, participant, str(extraction.nik).strip())
            except Exception:
                ok = False  # tidak cocok dengan data diri: jangan disahkan otomatis, user periksa manual
        if ok:
            participant.nik = str(extraction.nik).strip()
            ktp_doc.corrected_by_user = True  # dianggap terkonfirmasi (sumber: VLM, bukan koreksi manual)
            auto_confirmed = True

    db.commit()
    db.refresh(ktp_doc)
    db.refresh(participant)

    success = bool(extraction.nik and extraction.nama)
    ktp_confirmed = bool(participant.nik and ktp_doc.corrected_by_user)
    if auto_confirmed:
        message = "KTP terbaca lengkap dan langsung terkonfirmasi. Silakan lanjut."
    else:
        message = None if success else "Data tidak berhasil dibaca sepenuhnya. Silakan lengkapi secara manual."
        if not ktp_confirmed and success:
            message = message or "Periksa data lalu tekan Konfirmasi."
    if extraction.fallback_used:
        message = (message or "") + " (VLM tidak tersedia, dipakai Tesseract.)"

    return KtpOcrResult(
        success=success,
        ktp_document_id=ktp_doc.id,
        nik=extraction.nik,
        nama=extraction.nama,
        tempat_lahir=extraction.tempat_lahir,
        tanggal_lahir=extraction.tanggal_lahir,
        jenis_kelamin=extraction.jenis_kelamin,
        alamat=extraction.alamat,
        rt_rw=extraction.rt_rw,
        kelurahan=extraction.kelurahan,
        kecamatan=extraction.kecamatan,
        agama=extraction.agama,
        status_perkawinan=extraction.status_perkawinan,
        pekerjaan_ktp=extraction.pekerjaan_ktp,
        kewarganegaraan=extraction.kewarganegaraan,
        confidence=extraction.confidence,
        message=message,
        ocr_provider=extraction.provider,
        fallback_used=extraction.fallback_used,
        auto_confirmed=auto_confirmed,
        ktp_confirmed=ktp_confirmed,
    )


@router.post("/ktp/confirm", response_model=ParticipantOut)
def confirm_ktp_data(payload: KtpConfirm, db: Session = Depends(get_db)):
    """User mengoreksi/mengonfirmasi data hasil OCR sebelum disimpan permanen."""
    participant = db.query(Participant).filter(Participant.id == payload.participant_id).first()
    if not participant:
        raise not_found("Peserta tidak ditemukan", "PARTICIPANT_NOT_FOUND")

    # Data diri harus sama dengan KTP: nama sama, usia sama dengan hitungan dari tanggal lahir, NIK belum dipakai akun lain.
    ensure_ktp_matches_profile(participant, nama_ktp=payload.nama, tanggal_lahir=payload.tanggal_lahir)
    ensure_nik_available(db, participant, payload.nik)

    ktp_doc = db.query(KtpDocument).filter(KtpDocument.participant_id == payload.participant_id).first()
    if not ktp_doc:
        # Alur /api/ktp/scan bersifat stateless (tidak menyimpan apa pun sebelum user konfirmasi),
        # dan alur "Isi Manual" tidak mengunggah foto: dokumen dibuat di sini, tanpa gambar.
        ktp_doc = KtpDocument(
            participant_id=payload.participant_id,
            file_deleted=True,
            ocr_provider=payload.scan_provider or "manual",
            ocr_confidence=payload.scan_confidence,
            ocr_fallback_used=False,
        )
        db.add(ktp_doc)
    elif payload.scan_provider:
        ktp_doc.ocr_provider = payload.scan_provider
        ktp_doc.ocr_confidence = payload.scan_confidence

    participant.nik = payload.nik  # nama tidak diubah: sudah dipastikan sama dengan KTP

    for field in ["tempat_lahir", "tanggal_lahir", "jenis_kelamin", "alamat", "rt_rw",
                  "kelurahan", "kecamatan", "agama", "status_perkawinan",
                  "pekerjaan_ktp", "kewarganegaraan"]:
        value = getattr(payload, field, None)
        if value is not None:
            setattr(ktp_doc, field, value)
    ktp_doc.corrected_by_user = True

    db.commit()
    db.refresh(participant)
    return to_participant_out(participant)
