"""
Tesseract OCR (offline, gratis) sebagai provider cadangan untuk /api/ktp/scan.

Tesseract tidak memberi confidence per field, jadi setiap field yang terbaca diberi confidence tetap
di BAWAH threshold: semua kolom ditandai "Periksa kembali" dan user wajib memeriksanya.
"""
from __future__ import annotations

import io
import logging
import os
import re
import shutil

from app.core.config import settings
from app.services.vision.base import (
    KTP_FIELDS, ExtractionResult, FieldReading, VisionBadResponse, VisionNotConfigured, VisionProvider,
)

logger = logging.getLogger("app.vlm")

TESSERACT_CONFIDENCE = 0.5
TARGET_LONG_SIDE = 2400
_CHOICES = {
    "jenis_kelamin": ("LAKI-LAKI", "PEREMPUAN"),
    "agama": ("ISLAM", "KRISTEN", "KATOLIK", "HINDU", "BUDDHA", "KONGHUCU"),
    "status_perkawinan": ("BELUM KAWIN", "CERAI HIDUP", "CERAI MATI", "KAWIN"),
    "kewarganegaraan": ("WNI", "WNA"),
}
_JUNK_TAIL = re.compile(r"[\s|\\/_~`'\"\u201c\u201d.,:;\-]+$")
_JUNK_HEAD = re.compile(r"^[\s|\\/_~`'\"\u201c\u201d.,:;\-]+")


def tidy_values(values: dict, text: str) -> dict:
    """Bersihkan sampah khas OCR (mis. 'ISLAM ba', 'KAWIN \u201c4', 'PEREMPUAN Gol. Darah : B')."""
    out = {}
    for k, v in values.items():
        if not isinstance(v, str):
            out[k] = None
            continue
        v = _JUNK_HEAD.sub("", _JUNK_TAIL.sub("", v.strip()))
        if k in _CHOICES:
            up = v.upper()
            v = next((c for c in _CHOICES[k] if c in up), None)
        elif k not in ("nik", "tanggal_lahir", "rt_rw"):
            # KTP dicetak HURUF KAPITAL: token ekor yang bercampur huruf kecil / tanpa huruf-angka = sampah OCR.
            toks = v.split()
            while toks and (any(c.islower() for c in toks[-1]) or not any(c.isalnum() for c in toks[-1])):
                toks.pop()
            if k in ("nama", "tempat_lahir", "kelurahan", "kecamatan", "pekerjaan"):
                while toks and len(toks[0]) == 1:  # token 1 karakter di depan (mis. '1 PEGAWAI SWASTA')
                    toks.pop(0)
            v = _JUNK_TAIL.sub("", " ".join(toks))
        out[k] = v or None
    if out.get("rt_rw") and not re.fullmatch(r"\d{1,3}\s*/\s*\d{1,3}", out["rt_rw"]):
        m = re.search(r"\b(\d{3})\s*/\s*(\d{3})\b", text)
        out["rt_rw"] = f"{m.group(1)}/{m.group(2)}" if m else None
    elif not out.get("rt_rw"):
        m = re.search(r"\b(\d{3})\s*/\s*(\d{3})\b", text)
        out["rt_rw"] = f"{m.group(1)}/{m.group(2)}" if m else None
    return out
_DATE_RE = re.compile(r"(\d{1,2})[-/. ](\d{1,2})[-/. ](\d{4})")


class TesseractProvider(VisionProvider):
    name = "tesseract"

    def is_configured(self) -> bool:
        if settings.TESSERACT_CMD:
            return os.path.isfile(settings.TESSERACT_CMD)
        return shutil.which("tesseract") is not None

    def model_name(self) -> str:
        return "tesseract"

    def _complete(self, image_bytes: bytes, media_type: str) -> str:  # tidak dipakai; extract_ktp di-override
        raise NotImplementedError

    def extract_ktp(self, image_bytes: bytes, media_type: str) -> ExtractionResult:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as e:
            raise VisionNotConfigured("pytesseract belum terpasang di server.") from e
        if not self.is_configured():
            raise VisionNotConfigured("Pembaca KTP cadangan belum terpasang.")
        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

        from PIL import ImageOps
        from app.services.ocr_service import parse_ktp_text

        def ocr(img, psm: int) -> str:
            cfg = f"--psm {psm}"
            try:
                return pytesseract.image_to_string(img, lang="ind+eng", config=cfg, timeout=settings.VLM_TIMEOUT_S)
            except pytesseract.TesseractError:  # paket bahasa 'ind' belum terpasang
                return pytesseract.image_to_string(img, lang="eng", config=cfg, timeout=settings.VLM_TIMEOUT_S)

        try:
            with Image.open(io.BytesIO(image_bytes)) as src:
                # Teks KTP kecil dan di atas latar biru bercorak: grayscale + perbesar sangat membantu Tesseract.
                gray = ImageOps.autocontrast(ImageOps.grayscale(src), cutoff=1)
                scale = TARGET_LONG_SIDE / max(gray.size)
                big = gray.resize((max(1, int(gray.width * scale)), max(1, int(gray.height * scale))), Image.LANCZOS)
                texts = [ocr(big, 6), ocr(big, 4)]
        except pytesseract.TesseractNotFoundError as e:
            raise VisionNotConfigured("Pembaca KTP cadangan tidak ditemukan.") from e
        except Exception as e:
            logger.warning("Tesseract gagal: %s", type(e).__name__)
            raise VisionBadResponse("Foto KTP belum berhasil dibaca.") from None

        # Pakai hasil dengan field terbanyak.
        def filled(t: str) -> int:
            p = parse_ktp_text(t)
            return sum(1 for k in KTP_FIELDS if getattr(p, "pekerjaan_ktp" if k == "pekerjaan" else k, None))
        text = max(texts, key=filled)

        parsed = parse_ktp_text(text)

        values = {k: getattr(parsed, "pekerjaan_ktp" if k == "pekerjaan" else k, None) for k in KTP_FIELDS}
        # "Tempat/Tgl Lahir : BOGOR, 01-02-1995" biasanya terbaca satu baris: pisahkan tempat dan tanggal.
        combined = f"{values.get('tempat_lahir') or ''} {values.get('tanggal_lahir') or ''}"
        m = _DATE_RE.search(combined)
        if m:
            values["tanggal_lahir"] = f"{int(m.group(1)):02d}-{int(m.group(2)):02d}-{m.group(3)}"
            place = _DATE_RE.sub("", values.get("tempat_lahir") or "").strip(" ,:-")
            values["tempat_lahir"] = place or None
        else:
            values["tanggal_lahir"] = None

        values = tidy_values(values, text)
        fields = {
            k: FieldReading(value=(v.strip() if isinstance(v, str) and v.strip() else None),
                            confidence=TESSERACT_CONFIDENCE if v else 0.0)
            for k, v in values.items()
        }
        return ExtractionResult(
            document_type="KTP", confidence=TESSERACT_CONFIDENCE, fields=fields,
            warnings=["Dibaca dengan pembaca sederhana (akurasi terbatas). Periksa semua kolom dengan teliti."],
            provider=self.name, model=self.model_name(),
        )
