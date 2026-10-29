"""
OCR Service untuk KTP.
Menggunakan pytesseract (offline) sebagai default provider agar dapat berjalan
tanpa dependency eksternal berbayar. Provider lain (mis. Google Vision, cloud OCR)
dapat ditambahkan dengan mengimplementasikan interface yang sama, dipilih via
settings.OCR_PROVIDER.

PENTING: hasil OCR TIDAK PERNAH dianggap final. Selalu dikembalikan sebagai draft
yang wajib dikonfirmasi/dikoreksi oleh user sebelum disimpan sebagai data resmi.
"""
import re
import logging
from dataclasses import dataclass, asdict
from typing import Optional

from PIL import Image

logger = logging.getLogger("app.ocr")

NIK_RE = re.compile(r"\b(\d{16})\b")


@dataclass
class OcrExtraction:
    raw_text: str
    nik: Optional[str] = None
    nama: Optional[str] = None
    tempat_lahir: Optional[str] = None
    tanggal_lahir: Optional[str] = None
    jenis_kelamin: Optional[str] = None
    alamat: Optional[str] = None
    rt_rw: Optional[str] = None
    kelurahan: Optional[str] = None
    kecamatan: Optional[str] = None
    agama: Optional[str] = None
    status_perkawinan: Optional[str] = None
    pekerjaan_ktp: Optional[str] = None
    kewarganegaraan: Optional[str] = None
    confidence: int = 0
    # diisi oleh dispatcher: "tesseract" | "vlm"; fallback=True bila VLM gagal lalu Tesseract dipakai
    provider: str = "tesseract"
    fallback_used: bool = False
    fallback_reason: Optional[str] = None


def _extract_field(lines: list[str], label: str) -> Optional[str]:
    for line in lines:
        up = line.upper()
        if label in up:
            # format umum KTP: "LABEL : VALUE" atau "LABEL VALUE"
            after = line.split(":", 1)
            if len(after) == 2 and after[1].strip():
                return after[1].strip()
            parts = up.split(label, 1)
            if len(parts) == 2 and parts[1].strip(" :\n"):
                idx = line.upper().find(label) + len(label)
                val = line[idx:].strip(" :\n")
                if val:
                    return val
    return None


def run_ocr_on_image(file_path: str, provider_override: Optional[str] = None) -> OcrExtraction:
    """Dispatcher provider. `provider_override`: tesseract | vlm | auto | None (pakai settings)."""
    from app.core.config import settings
    requested = (provider_override or settings.OCR_PROVIDER or "tesseract").lower()
    if requested not in ("tesseract", "vlm", "auto"):
        logger.warning(f"OCR_PROVIDER tidak dikenal: {requested}, fallback ke tesseract")
        requested = "tesseract"

    if requested == "tesseract":
        return run_tesseract_on_image(file_path)

    # requested vlm / auto -> coba VLM dulu
    from app.services import vlm_service
    if not vlm_service.is_vlm_configured():
        if requested == "vlm":
            logger.error("OCR_PROVIDER=vlm tapi VLM belum dikonfigurasi")
            err = OcrExtraction(raw_text="", confidence=0, provider="vlm")
            return err
        logger.info("VLM belum dikonfigurasi, pakai Tesseract")
        r = run_tesseract_on_image(file_path)
        r.fallback_used = True
        r.fallback_reason = "vlm_not_configured"
        return r

    try:
        vr = vlm_service.extract_ktp_with_vlm(file_path)
        ext = OcrExtraction(raw_text=vr.raw_text, confidence=vr.confidence, provider="vlm", **vr.fields)
        return ext
    except Exception as e:
        logger.warning(f"VLM gagal ({type(e).__name__}), fallback ke Tesseract")
        if requested == "vlm":
            # mode vlm murni: kembalikan hasil kosong tapi tandai provider agar caller bisa 502 tegas.
            # routes akan mengubahnya jadi error jelas; di sini tetap fallback-info agar tidak diam-diam.
            err = OcrExtraction(raw_text="", confidence=0, provider="vlm",
                                fallback_used=False, fallback_reason=type(e).__name__)
            return err
        r = run_tesseract_on_image(file_path)
        r.fallback_used = True
        r.fallback_reason = type(e).__name__
        return r


def run_tesseract_on_image(file_path: str) -> OcrExtraction:
    try:
        import pytesseract
    except ImportError:
        logger.error("pytesseract tidak terinstal")
        return OcrExtraction(raw_text="", confidence=0)

    # On Windows especially, the tesseract binary is often not on PATH even
    # after installation. Allow an explicit override via TESSERACT_CMD so
    # users don't need to fight with system PATH configuration.
    from app.core.config import settings
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    try:
        image = Image.open(file_path)
        raw_text = pytesseract.image_to_string(image, lang="ind+eng")
    except pytesseract.TesseractNotFoundError:
        logger.error(
            "Tesseract binary tidak ditemukan. Pastikan Tesseract OCR terinstal di sistem "
            "dan/atau set TESSERACT_CMD di .env ke path executable-nya."
        )
        return OcrExtraction(raw_text="", confidence=0)
    except Exception as e:
        logger.error(f"OCR gagal memproses file: {type(e).__name__}")
        return OcrExtraction(raw_text="", confidence=0)

    return parse_ktp_text(raw_text)


def parse_ktp_text(raw_text: str) -> OcrExtraction:
    """Turn raw OCR text into KTP fields. Pure function: no tesseract needed, easy to test."""
    lines = [l for l in raw_text.split("\n") if l.strip()]
    nik_match = NIK_RE.search(raw_text.replace(" ", ""))

    extraction = OcrExtraction(
        raw_text=raw_text,
        nik=nik_match.group(1) if nik_match else None,
        nama=_extract_field(lines, "NAMA"),
        tempat_lahir=_extract_field(lines, "TEMPAT"),
        tanggal_lahir=_extract_field(lines, "LAHIR"),
        jenis_kelamin=_extract_field(lines, "KELAMIN"),
        alamat=_extract_field(lines, "ALAMAT"),
        rt_rw=_extract_field(lines, "RT/RW") or _extract_field(lines, "RT"),
        # "KEL" alone would also match the "KELAMIN" line, so use the full labels.
        kelurahan=(_extract_field(lines, "KEL/DESA") or _extract_field(lines, "KELURAHAN")
                   or _extract_field(lines, "DESA")),
        kecamatan=_extract_field(lines, "KECAMATAN"),
        agama=_extract_field(lines, "AGAMA"),
        status_perkawinan=_extract_field(lines, "PERKAWINAN"),
        pekerjaan_ktp=_extract_field(lines, "PEKERJAAN"),
        kewarganegaraan=_extract_field(lines, "KEWARGANEGARAAN"),
    )

    # confidence kasar berdasarkan jumlah field yang berhasil terisi
    fields = asdict(extraction)
    fields.pop("raw_text")
    fields.pop("confidence")
    fields.pop("provider", None)
    fields.pop("fallback_used", None)
    fields.pop("fallback_reason", None)
    filled = sum(1 for v in fields.values() if v)
    extraction.confidence = int((filled / len(fields)) * 100) if fields else 0

    return extraction