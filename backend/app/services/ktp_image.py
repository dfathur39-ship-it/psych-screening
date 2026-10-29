"""
Validasi + preprocessing gambar KTP sebelum dikirim ke VLM. Semua di memori (tidak menulis ke disk).

Validasi: ukuran, ekstensi, MIME yang dideklarasikan, magic bytes (isi file sebenarnya),
decode penuh dengan Pillow (deteksi file korup), dan dimensi.
Preprocessing (opsional, gagal -> pakai gambar asli): putar sesuai EXIF, perkecil, autocontrast
ringan, sharpening ringan, re-encode JPEG (sekaligus membuang metadata EXIF/GPS).
"""
from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageFilter, ImageOps

from app.core.config import settings

logger = logging.getLogger("app.ktp_image")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_PIXELS = 60_000_000


class ImageValidationError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


@dataclass
class PreparedImage:
    data: bytes
    media_type: str
    width: int
    height: int
    preprocessed: bool


def sniff_media_type(data: bytes) -> Optional[str]:
    """Tentukan tipe gambar dari magic bytes, bukan dari nama/header yang dikirim client."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image(data: bytes, filename: Optional[str], content_type: Optional[str]) -> tuple[str, int, int]:
    """Return (media_type, width, height) atau raise ImageValidationError."""
    max_bytes = int(float(settings.MAX_KTP_FILE_SIZE_MB) * 1024 * 1024)
    if len(data) == 0:
        raise ImageValidationError("EMPTY_FILE", "File kosong.")
    if len(data) > max_bytes:
        raise ImageValidationError(
            "FILE_TOO_LARGE", f"Ukuran file maksimal {settings.MAX_KTP_FILE_SIZE_MB:g} MB.", 413)

    ext = os.path.splitext(filename or "")[1].lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise ImageValidationError("INVALID_FILE_TYPE", "Format file harus JPG, PNG, atau WEBP.")
    if content_type and content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise ImageValidationError("INVALID_FILE_TYPE", "Format file harus JPG, PNG, atau WEBP.")

    media_type = sniff_media_type(data[:32])
    if media_type is None:
        # termasuk executable (MZ/ELF), HTML, script, PDF, dll.
        raise ImageValidationError("INVALID_FILE_TYPE", "Isi file bukan gambar JPG, PNG, atau WEBP yang valid.")

    try:
        with Image.open(io.BytesIO(data)) as probe:
            width, height = probe.size
            if width * height > MAX_PIXELS or max(width, height) > settings.KTP_MAX_IMAGE_SIDE_PX:
                raise ImageValidationError("IMAGE_DIMENSIONS_TOO_LARGE", "Dimensi gambar terlalu besar.")
            if min(width, height) < settings.KTP_MIN_IMAGE_SIDE_PX:
                raise ImageValidationError(
                    "IMAGE_TOO_SMALL", "Resolusi gambar terlalu kecil. Foto ulang dengan lebih dekat dan jelas.")
            probe.verify()
        with Image.open(io.BytesIO(data)) as full:
            full.load()  # decode penuh: file terpotong/korup gagal di sini
    except ImageValidationError:
        raise
    except Image.DecompressionBombError:
        raise ImageValidationError("IMAGE_DIMENSIONS_TOO_LARGE", "Dimensi gambar terlalu besar.") from None
    except Exception:
        raise ImageValidationError("INVALID_IMAGE", "Gambar rusak atau tidak dapat dibuka.") from None
    return media_type, width, height


def _preprocess(data: bytes) -> tuple[bytes, int, int]:
    with Image.open(io.BytesIO(data)) as src:
        img = ImageOps.exif_transpose(src)
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        limit = settings.KTP_VLM_IMAGE_MAX_SIDE_PX
        if max(img.size) > limit:
            img.thumbnail((limit, limit), Image.Resampling.LANCZOS)

        img = ImageOps.autocontrast(img, cutoff=1)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=3))

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90, optimize=True)
        return out.getvalue(), img.width, img.height


def prepare_image(data: bytes, filename: Optional[str], content_type: Optional[str]) -> PreparedImage:
    """Validasi lalu (bila diaktifkan) preprocessing. Preprocessing gagal -> gambar asli."""
    media_type, width, height = validate_image(data, filename, content_type)
    if not settings.KTP_PREPROCESS:
        return PreparedImage(data, media_type, width, height, preprocessed=False)
    try:
        processed, w, h = _preprocess(data)
        return PreparedImage(processed, "image/jpeg", w, h, preprocessed=True)
    except Exception as e:
        logger.warning("Preprocessing gambar KTP gagal (%s), pakai gambar asli", type(e).__name__)
        return PreparedImage(data, media_type, width, height, preprocessed=False)
