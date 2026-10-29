"""
Validasi hasil VLM oleh backend. Hasil AI TIDAK PERNAH dianggap benar secara otomatis:
setiap field mendapat status `ok` / `review` / `unreadable`, dan field yang melanggar aturan
(NIK bukan 16 digit, tanggal tidak valid) dikosongkan (null) alih-alih dipercaya.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from app.services.vision.base import KTP_FIELDS, ExtractionResult

STATUS_OK = "ok"
STATUS_REVIEW = "review"
STATUS_UNREADABLE = "unreadable"

_KTP_TYPES = ("KTP", "E-KTP", "EKTP", "KARTU TANDA PENDUDUK")
_DATE_PATTERNS = (
    re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$"),   # YYYY-MM-DD
    re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$"),   # DD-MM-YYYY
)
_LONG_NUMBER = re.compile(r"\d{8,}")


@dataclass
class ValidatedKtp:
    is_ktp: bool = True
    data: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
    field_status: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    overall_confidence: Optional[float] = None

    @property
    def filled_count(self) -> int:
        return sum(1 for v in self.data.values() if v)

    @property
    def needs_review(self) -> list:
        return [k for k in KTP_FIELDS if self.field_status.get(k) != STATUS_OK]

    @property
    def readable(self) -> bool:
        # kurang dari 2 field terbaca = dianggap tidak terbaca
        return self.filled_count >= 2


def normalize_date(value: Optional[str], today: Optional[date] = None) -> Optional[str]:
    """Return 'YYYY-MM-DD' bila tanggal nyata & masuk akal, selain itu None."""
    if not value:
        return None
    s = value.strip()
    today = today or date.today()
    y = m = d = None
    for i, pat in enumerate(_DATE_PATTERNS):
        match = pat.match(s)
        if match:
            a, b, c = (int(x) for x in match.groups())
            y, m, d = (a, b, c) if i == 0 else (c, b, a)
            break
    if y is None:
        return None
    try:
        parsed = date(y, m, d)
    except ValueError:
        return None
    if parsed.year < 1900 or parsed > today:
        return None
    return parsed.isoformat()


def normalize_nik(value: Optional[str]) -> Optional[str]:
    """NIK harus 16 digit angka (spasi/strip dibuang). Selain itu None."""
    if not value:
        return None
    digits = re.sub(r"[\s.\-]", "", value)
    return digits if re.fullmatch(r"\d{16}", digits) else None


def _nik_birth_parts(nik: str) -> tuple[int, int, int]:
    day, month, yy = int(nik[6:8]), int(nik[8:10]), int(nik[10:12])
    if day > 40:  # perempuan: tanggal lahir + 40
        day -= 40
    return day, month, yy


def _safe_model_warning(w: str) -> Optional[str]:
    """Buang peringatan dari model yang mungkin menyalin data KTP (angka panjang)."""
    w = " ".join(w.split())
    if not w or _LONG_NUMBER.search(w):
        return None
    return w[:200]


def is_ktp_document_type(doc_type: Optional[str]) -> bool:
    if not doc_type:
        return True  # tidak disebut -> nilai dari field yang terbaca
    t = doc_type.upper().strip()
    return any(t == k or t.startswith(k) for k in _KTP_TYPES)


def validate_extraction(result: ExtractionResult, threshold: float, today: Optional[date] = None) -> ValidatedKtp:
    out = ValidatedKtp()
    out.is_ktp = is_ktp_document_type(result.document_type)
    warnings: list[str] = []

    values: dict[str, Optional[str]] = {}
    confs: dict[str, Optional[float]] = {}
    for key in KTP_FIELDS:
        reading = result.fields.get(key)
        values[key] = reading.value if reading else None
        c = reading.confidence if reading else None
        confs[key] = c if c is not None else (result.confidence if values[key] else None)

    # ---- aturan per field ----
    forced_review: set[str] = set()

    if values["nik"]:
        nik = normalize_nik(values["nik"])
        if nik is None:
            warnings.append("NIK tidak valid (harus 16 digit angka). Isi NIK secara manual.")
        values["nik"] = nik

    if values["tanggal_lahir"]:
        iso = normalize_date(values["tanggal_lahir"], today)
        if iso is None:
            warnings.append("Tanggal lahir tidak valid atau tidak terbaca. Isi tanggal secara manual.")
        values["tanggal_lahir"] = iso

    if values["nama"]:
        if len(values["nama"]) < 2 or re.search(r"\d", values["nama"]):
            warnings.append("Nama tampak tidak wajar (terlalu pendek atau mengandung angka). Periksa kembali.")
            forced_review.add("nama")
    else:
        warnings.append("Nama tidak terbaca.")

    if values["rt_rw"] and not re.fullmatch(r"\d{1,3}\s*/\s*\d{1,3}", values["rt_rw"]):
        forced_review.add("rt_rw")

    # Cross-check NIK vs tanggal lahir (NIK memuat tanggal lahir; perempuan +40 pada tanggal).
    if values["nik"] and values["tanggal_lahir"]:
        day, month, yy = _nik_birth_parts(values["nik"])
        y, m, d = (int(x) for x in values["tanggal_lahir"].split("-"))
        if (day, month, yy) != (d, m, y % 100):
            warnings.append("NIK dan tanggal lahir tidak cocok. Periksa keduanya dengan KTP asli.")
            forced_review.update({"nik", "tanggal_lahir"})

    # ---- status per field ----
    status: dict[str, str] = {}
    for key in KTP_FIELDS:
        if not values[key]:
            status[key] = STATUS_UNREADABLE
        elif key in forced_review or confs[key] is None or confs[key] < threshold:
            status[key] = STATUS_REVIEW
        else:
            status[key] = STATUS_OK

    # ---- peringatan dari model (disaring) ----
    for w in result.warnings:
        safe = _safe_model_warning(w)
        if safe:
            warnings.append(safe)
    n_review = sum(1 for s in status.values() if s == STATUS_REVIEW)
    n_unread = sum(1 for s in status.values() if s == STATUS_UNREADABLE)
    if n_unread and n_unread < len(KTP_FIELDS):
        warnings.append(f"{n_unread} kolom tidak terbaca. Lengkapi secara manual.")
    if n_review:
        warnings.append(f"{n_review} kolom perlu diperiksa karena tingkat keyakinan rendah.")

    present_confs = [c for k, c in confs.items() if values[k] and c is not None]
    overall = result.confidence
    if overall is None and present_confs:
        overall = sum(present_confs) / len(present_confs)

    out.data = values
    out.confidence = {k: (round(confs[k], 4) if confs[k] is not None else None) for k in KTP_FIELDS}
    out.field_status = status
    out.warnings = list(dict.fromkeys(warnings))  # dedupe, urutan tetap
    out.overall_confidence = round(overall, 4) if overall is not None else None
    return out
