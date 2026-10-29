"""
POST /api/ktp/scan — baca KTP dengan VLM (stateless).

- Tidak menyimpan gambar (diproses di memori) dan TIDAK menyimpan hasil ke database.
  Penyimpanan terjadi hanya setelah user memeriksa data dan menekan Konfirmasi
  (POST /api/ocr/ktp/confirm).
- Akses dibatasi: peserta harus ada, rate limit per IP, kuota per peserta dan global.
- Tidak ada isi KTP / NIK / gambar di log maupun pesan error.
"""
import logging
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import not_found
from app.core.limiter import limiter
from app.models.models import Participant
from app.schemas.ktp_scan import KtpScanData, KtpScanError, KtpScanResponse
from app.services.ktp_image import ImageValidationError, prepare_image
from app.services.ktp_validation import validate_extraction
from app.services.participant_service import is_valid_uuid
from app.services.scan_quota import quota
from app.services.vision import VisionError, VisionNotConfigured, get_provider
from app.services.vision.tesseract_provider import TesseractProvider

router = APIRouter(prefix="/api/ktp", tags=["ktp-scan"])
logger = logging.getLogger("app.ktp_scan")


def _error(status_code: int, message: str, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={
        "success": False, "message": message, "error_code": code, "can_fill_manually": True,
    })


@router.post(
    "/scan",
    response_model=KtpScanResponse,
    summary="Scan KTP dengan AI (VLM)",
    description=(
        "Unggah foto/scan KTP (JPG/PNG/WEBP) untuk dibaca VLM. Hasil berupa **draft**: tidak disimpan, "
        "dan wajib diperiksa user lalu dikonfirmasi lewat `POST /api/ocr/ktp/confirm`. "
        "Field yang tidak terbaca bernilai `null`; field dengan confidence di bawah threshold "
        "ditandai `review` di `field_status`."
    ),
    responses={
        400: {"model": KtpScanError, "description": "File tidak valid (tipe/isi/korup/terlalu kecil)"},
        404: {"model": KtpScanError, "description": "Peserta tidak ditemukan"},
        413: {"model": KtpScanError, "description": "File terlalu besar"},
        422: {"model": KtpScanError, "description": "Dokumen bukan KTP / tidak dapat dibaca"},
        429: {"model": KtpScanError, "description": "Rate limit / kuota scan / rate limit provider AI"},
        500: {"model": KtpScanError, "description": "Internal server error"},
        502: {"model": KtpScanError, "description": "Respons provider AI tidak valid"},
        503: {"model": KtpScanError, "description": "Provider AI tidak tersedia / belum dikonfigurasi"},
        504: {"model": KtpScanError, "description": "Provider AI timeout"},
    },
)
@limiter.limit(lambda: settings.KTP_SCAN_RATE_LIMIT)
async def scan_ktp(
    request: Request,
    participant_id: str = Form(..., description="ID peserta (dari langkah data diri)"),
    file: UploadFile = File(..., description="Foto/scan KTP: JPG, PNG, atau WEBP"),
    db: Session = Depends(get_db),
):
    started = time.monotonic()

    participant = (
        db.query(Participant).filter(Participant.id == participant_id).first()
        if is_valid_uuid(participant_id) else None
    )
    if not participant:
        raise not_found("Peserta tidak ditemukan", "PARTICIPANT_NOT_FOUND")

    # Baca maksimal batas+1 byte: file raksasa tidak pernah dimuat utuh ke memori.
    max_bytes = int(float(settings.MAX_KTP_FILE_SIZE_MB) * 1024 * 1024)
    raw = await file.read(max_bytes + 1)

    try:
        prepared = await run_in_threadpool(prepare_image, raw, file.filename, file.content_type)
    except ImageValidationError as e:
        raise _error(e.http_status, e.message, e.code) from None
    finally:
        del raw

    # OCR_PROVIDER: vlm = hanya AI | tesseract = hanya Tesseract | auto = AI dulu, Tesseract bila AI gagal.
    # Nilai tidak dikenal diperlakukan sebagai tesseract (sama dengan alur lama).
    mode = (settings.OCR_PROVIDER or "tesseract").lower()
    if mode not in ("vlm", "auto", "tesseract"):
        mode = "tesseract"

    chain: list = []
    first_error: VisionError | None = None
    if mode in ("vlm", "auto"):
        try:
            chain.append(get_provider())
        except VisionError as e:
            first_error = e
    if mode in ("tesseract", "auto"):
        chain.append(TesseractProvider())

    extraction = None
    fallback_used = False
    for provider in chain:
        if not provider.is_configured():
            first_error = first_error or VisionNotConfigured()
            continue
        if provider.name != "tesseract":
            # Hanya pemanggilan VLM (berbayar) yang memakai kuota; yang tidak dikonfigurasi tidak menghabiskannya.
            if not quota.try_acquire(f"p:{participant_id}", settings.KTP_SCAN_MAX_PER_PARTICIPANT, settings.KTP_SCAN_WINDOW_S) \
                    or not quota.try_acquire("global", settings.KTP_SCAN_GLOBAL_MAX_PER_WINDOW, settings.KTP_SCAN_WINDOW_S):
                raise _error(429, "Batas scan KTP tercapai. Coba lagi nanti atau isi data secara manual.", "SCAN_QUOTA_EXCEEDED")
        try:
            extraction = await run_in_threadpool(provider.extract_ktp, prepared.data, prepared.media_type)
            fallback_used = provider.name == "tesseract" and mode == "auto"
            break
        except VisionError as e:
            first_error = first_error or e
            logger.warning("ktp_scan provider=%s gagal: %s", provider.name, e.code)
    if extraction is None:
        e = first_error or VisionNotConfigured()
        raise _error(e.http_status, e.message, e.code)

    validated = validate_extraction(extraction, settings.VLM_CONFIDENCE_THRESHOLD)
    if not validated.is_ktp:
        raise _error(422, "Dokumen yang diunggah bukan KTP. Unggah foto KTP yang benar atau isi manual.", "NOT_A_KTP")
    if not validated.readable:
        raise _error(422, "KTP tidak dapat dibaca. Foto ulang dengan pencahayaan cukup, atau isi manual.", "KTP_UNREADABLE")

    needs_review = validated.needs_review
    message = ("Data KTP berhasil dibaca. Silakan periksa kembali."
               if not needs_review else
               "Data KTP berhasil dibaca, tetapi beberapa kolom perlu diperiksa. Silakan periksa kembali.")
    if fallback_used:
        message += " (AI tidak tersedia, dipakai OCR Tesseract.)"
    logger.info(
        "ktp_scan ok provider=%s model=%s filled=%d review=%d preprocessed=%s ms=%d",
        extraction.provider, extraction.model, validated.filled_count, len(needs_review),
        prepared.preprocessed, int((time.monotonic() - started) * 1000),
    )
    return KtpScanResponse(
        success=True,
        message=message,
        data=KtpScanData(**validated.data),
        confidence=validated.confidence,
        field_status=validated.field_status,
        needs_review=needs_review,
        warnings=validated.warnings,
        overall_confidence=validated.overall_confidence,
        confidence_threshold=settings.VLM_CONFIDENCE_THRESHOLD,
        provider=extraction.provider,
        model=extraction.model,
        saved=False,
        fallback_used=fallback_used,
    )
