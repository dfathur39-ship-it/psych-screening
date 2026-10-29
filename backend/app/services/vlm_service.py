"""
VLM Service untuk KTP (alur lama /api/ocr/ktp).

Provider dipilih lewat VLM_PROVIDER (anthropic | openai | local) — lihat app/services/vision/.
Alur baru stateless ada di app/routes/ktp_scan.py (POST /api/ktp/scan).

Dipakai sebagai alternatif/pelengkap Tesseract via `OCR_PROVIDER`:
  - `tesseract` : hanya Tesseract offline (default, backward-compatible)
  - `vlm`       : hanya VLM, error tegas kalau tidak dikonfigurasi/gagal
  - `auto`      : coba VLM dulu (kalau dikonfigurasi), fallback ke Tesseract

Privacy: jangan pernah log image base64 / NIK / raw hasil VLM.
Hasil VLM TIDAK PERNAH final — selalu jadi draft yang wajib dikonfirmasi user.
"""
import base64
import json
import logging
import mimetypes
import os
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("app.vlm")

NIK_RE = re.compile(r"\b(\d{16})\b")

KTP_FIELDS = (
    "nik", "nama", "tempat_lahir", "tanggal_lahir", "jenis_kelamin",
    "alamat", "rt_rw", "kelurahan", "kecamatan", "agama",
    "status_perkawinan", "pekerjaan_ktp", "kewarganegaraan",
)

SYSTEM_PROMPT = (
    "Kamu mengekstrak data dari foto KTP Indonesia. "
    "Kembalikan HANYA JSON valid dengan key persis: "
    "nik, nama, tempat_lahir, tanggal_lahir, jenis_kelamin, alamat, rt_rw, "
    "kelurahan, kecamatan, agama, status_perkawinan, pekerjaan_ktp, kewarganegaraan. "
    "Aturan: nik 16 digit angka atau null; tanggal_lahir format DD-MM-YYYY atau null; "
    "jangan mengarang — pakai null bila tidak terbaca; semua huruf sesuai yang tertulis."
)

USER_PROMPT = (
    "Baca foto KTP ini dan kembalikan JSON sesuai skema. "
    'Contoh: {"nik":"3171...","nama":"BUDI SANTOSO",...}. Hanya JSON, tanpa penjelasan.'
)


@dataclass
class VlmResult:
    fields: dict
    raw_text: str  # JSON mentah dari model (untuk audit, disimpan seperti ocr_raw_text)
    confidence: int


def is_vlm_configured() -> bool:
    """True kalau provider VLM terpilih (VLM_PROVIDER) cukup dikonfigurasi (tanpa membocorkan key)."""
    from app.services.vision import is_vlm_configured as _configured
    return _configured()


def _guess_mime(file_path: str) -> str:
    mime, _ = mimetypes.guess_type(file_path)
    if mime in ("image/jpeg", "image/png", "image/webp"):
        return mime
    # fallback dari ekstensi umum
    ext = os.path.splitext(file_path)[1].lower()
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")


def _image_to_data_url(file_path: str) -> str:
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{_guess_mime(file_path)};base64,{b64}"


def _parse_model_json(content: str) -> dict:
    """Ambil JSON dari jawaban model (toleran terhadap ```json fence)."""
    text = (content or "").strip()
    if text.startswith("```"):
        # buang fence ```json ... ```
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    # kalau ada teks tambahan, ambil blok {...} pertama-terakhir
    if not text.startswith("{"):
        m = re.search(r"\{.*\}", text, re.DOTALL)
        text = m.group(0) if m else "{}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("VLM mengembalikan non-JSON")
        return {}
    return data if isinstance(data, dict) else {}


def _clean(value) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("null", "none", "-", "--"):
        return None
    return s


def _confidence_from_fields(fields: dict) -> int:
    filled = sum(1 for k in KTP_FIELDS if fields.get(k))
    return int((filled / len(KTP_FIELDS)) * 100) if KTP_FIELDS else 0


def extract_ktp_with_vlm(file_path: str) -> VlmResult:
    """
    Alur lama (/api/ocr/ktp): baca file, panggil provider VLM terpilih (VLM_PROVIDER).
    Raises RuntimeError (VisionError) bila tidak dikonfigurasi atau gagal —
    caller yang memutuskan fallback ke Tesseract.
    """
    from app.services.vision import get_provider

    if not is_vlm_configured():
        raise RuntimeError("VLM belum dikonfigurasi (cek VLM_PROVIDER / API key / VLM_MODEL)")

    with open(file_path, "rb") as f:
        image_bytes = f.read()
    result = get_provider().extract_ktp(image_bytes, _guess_mime(file_path))

    # Alur lama memakai nama field `pekerjaan_ktp`.
    values = {k: _clean(r.value) for k, r in result.fields.items()}
    fields = {k: values.get(k if k != "pekerjaan_ktp" else "pekerjaan") for k in KTP_FIELDS}

    # validasi ringan: NIK harus 16 digit, kalau tidak — null-kan (jangan percaya model)
    nik = fields.get("nik")
    if nik:
        digits = re.sub(r"\D", "", nik)
        m = NIK_RE.search(digits)
        fields["nik"] = m.group(1) if m else None

    raw = json.dumps(fields, ensure_ascii=False)
    return VlmResult(fields=fields, raw_text=raw, confidence=_confidence_from_fields(fields))
