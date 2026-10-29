"""Parsing jawaban VLM menjadi ExtractionResult. Toleran terhadap format, ketat terhadap isi."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from app.services.vision.base import (
    KTP_FIELDS, ExtractionResult, FieldReading, VisionBadResponse,
)

logger = logging.getLogger("app.vlm")

# Nama alternatif yang dipakai alur lama / model.
_ALIASES = {"pekerjaan_ktp": "pekerjaan"}


def clean_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    s = str(value).strip()
    if not s or s.lower() in ("null", "none", "n/a", "-", "--"):
        return None
    return s


def normalize_confidence(value: Any) -> Optional[float]:
    """Terima 0-1 atau 0-100 (persen). Return None bila bukan angka."""
    if value is None or isinstance(value, bool):
        return None
    try:
        c = float(value)
    except (TypeError, ValueError):
        return None
    if c != c:  # NaN
        return None
    if c > 1.0:
        c = c / 100.0
    return max(0.0, min(1.0, c))


def extract_json_object(text: str) -> dict:
    """Ambil objek JSON dari teks jawaban (buang ```json fence / teks pengantar bila ada)."""
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    candidates = [s]
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m and m.group(0) != s:
        candidates.append(m.group(0))
    for cand in candidates:
        try:
            data = json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            return data
    raise VisionBadResponse()


def parse_model_output(text: str) -> ExtractionResult:
    """
    Terima dua bentuk:
      - skema lengkap: {"document_type","confidence","fields":{k:{"value","confidence"}},"warnings":[]}
      - skema datar (alur lama): {"nik": "...", "nama": "...", ...}
    Raise VisionBadResponse bila bukan JSON object.
    """
    data = extract_json_object(text)

    raw_fields = data.get("fields") if isinstance(data.get("fields"), dict) else data
    fields: dict[str, FieldReading] = {}
    for key in KTP_FIELDS:
        raw = raw_fields.get(key)
        if raw is None:
            for alias, canonical in _ALIASES.items():
                if canonical == key and alias in raw_fields:
                    raw = raw_fields[alias]
        if isinstance(raw, dict):
            fields[key] = FieldReading(
                value=clean_value(raw.get("value")),
                confidence=normalize_confidence(raw.get("confidence")),
            )
        else:
            fields[key] = FieldReading(value=clean_value(raw), confidence=None)

    warnings_raw = data.get("warnings")
    warnings = [str(w).strip() for w in warnings_raw if str(w).strip()] if isinstance(warnings_raw, list) else []

    doc_type = clean_value(data.get("document_type"))
    return ExtractionResult(
        document_type=doc_type.upper() if doc_type else None,
        confidence=normalize_confidence(data.get("confidence")),
        fields=fields,
        warnings=warnings,
    )
