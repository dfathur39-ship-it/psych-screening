"""Validasi hasil VLM oleh backend: NIK, tanggal, nama, confidence, field kosong."""
from datetime import date

from app.services.ktp_validation import (
    STATUS_OK, STATUS_REVIEW, STATUS_UNREADABLE, normalize_date, normalize_nik, validate_extraction,
)
from app.services.vision.parsing import parse_model_output
from tests.ktp_fixtures import VALID_NIK, vlm_json

TODAY = date(2026, 10, 26)


def _validate(text, threshold=0.80):
    return validate_extraction(parse_model_output(text), threshold, today=TODAY)


def test_valid_result_all_ok():
    v = _validate(vlm_json())
    assert v.is_ktp and v.readable
    assert v.data["nik"] == VALID_NIK and v.data["tanggal_lahir"] == "1995-02-01"
    assert set(v.field_status.values()) == {STATUS_OK}
    assert v.needs_review == [] and v.overall_confidence == 0.97


def test_low_confidence_flagged_for_review():
    v = _validate(vlm_json(alamat=("JL MERDEKA NO 1", 0.55)))
    assert v.field_status["alamat"] == STATUS_REVIEW
    assert v.needs_review == ["alamat"]
    assert any("perlu diperiksa" in w for w in v.warnings)


def test_threshold_is_configurable():
    text = vlm_json(alamat=("JL MERDEKA", 0.85))
    assert _validate(text, 0.80).field_status["alamat"] == STATUS_OK
    assert _validate(text, 0.90).field_status["alamat"] == STATUS_REVIEW


def test_missing_fields_are_null_and_unreadable():
    v = _validate(vlm_json(kelurahan=(None, 0.1), kecamatan=(None, 0.0)))
    assert v.data["kelurahan"] is None and v.field_status["kelurahan"] == STATUS_UNREADABLE
    assert "kecamatan" in v.needs_review
    assert any("tidak terbaca" in w for w in v.warnings)


def test_invalid_nik_is_nulled():
    for bad in ("123", "31712301029500", "31712301029500011", "ABCDEFGHIJKLMNOP"):
        v = _validate(vlm_json(nik=bad))
        assert v.data["nik"] is None and v.field_status["nik"] == STATUS_UNREADABLE, bad
        assert any("NIK tidak valid" in w for w in v.warnings)


def test_nik_with_spaces_is_normalized():
    assert normalize_nik("3171 2301 0295 0001") == VALID_NIK
    assert normalize_nik("3171-2301-0295-0001") == VALID_NIK


def test_invalid_dates_are_nulled():
    for bad in ("1995-13-45", "31-02-1995", "2999-01-01", "1850-01-01", "kemarin", "95-02-01"):
        v = _validate(vlm_json(tanggal_lahir=bad))
        assert v.data["tanggal_lahir"] is None, bad
        assert v.field_status["tanggal_lahir"] == STATUS_UNREADABLE


def test_date_formats_normalized_to_iso():
    assert normalize_date("01-02-1995", TODAY) == "1995-02-01"
    assert normalize_date("01/02/1995", TODAY) == "1995-02-01"
    assert normalize_date("1995-02-01", TODAY) == "1995-02-01"


def test_nik_and_birthdate_mismatch_flags_both_for_review():
    v = _validate(vlm_json(tanggal_lahir="1990-07-09"))
    assert v.field_status["nik"] == STATUS_REVIEW and v.field_status["tanggal_lahir"] == STATUS_REVIEW
    assert any("tidak cocok" in w for w in v.warnings)


def test_female_nik_day_plus_40_matches():
    # perempuan lahir 01-02-1995 -> DD pada NIK = 41
    v = _validate(vlm_json(nik="3171234102950001", jenis_kelamin="PEREMPUAN"))
    assert v.field_status["nik"] == STATUS_OK


def test_empty_name_flagged():
    v = _validate(vlm_json(nama=(None, 0.0)))
    assert v.field_status["nama"] == STATUS_UNREADABLE
    assert any("Nama tidak terbaca" in w for w in v.warnings)


def test_name_with_digits_flagged_for_review():
    v = _validate(vlm_json(nama="BUD1 S4NTOSO"))
    assert v.field_status["nama"] == STATUS_REVIEW


def test_non_ktp_document():
    v = _validate('{"document_type": "BUKAN_KTP", "confidence": 0.9, "fields": {}, "warnings": []}')
    assert v.is_ktp is False


def test_unreadable_when_almost_nothing_found():
    v = _validate('{"document_type": "KTP", "confidence": 0.1, "fields": {"nama": {"value": "BUDI", "confidence": 0.3}}, "warnings": ["gambar buram"]}')
    assert v.readable is False
    assert "gambar buram" in v.warnings


def test_model_warning_that_copies_digits_is_dropped():
    text = '{"document_type":"KTP","confidence":0.9,"fields":{"nik":{"value":"3171230102950001","confidence":0.9},"nama":{"value":"BUDI","confidence":0.9}},"warnings":["NIK 3171230102950001 buram","foto agak miring"]}'
    v = _validate(text)
    assert "foto agak miring" in v.warnings
    assert not any("3171230102950001" in w for w in v.warnings)
