"""POST /api/ktp/scan end-to-end dengan provider palsu (tanpa API berbayar)."""
import logging

import pytest

from app.core.config import settings
from app.core.limiter import limiter
from app.models.models import KtpDocument, Participant
from app.services.scan_quota import quota
from app.services.vision.base import (
    VisionBadResponse, VisionNotConfigured, VisionProvider, VisionRateLimited, VisionTimeout, VisionUnavailable,
)
from tests.conftest import make_participant
from tests.ktp_fixtures import VALID_NIK, make_image_bytes, vlm_json


class FakeProvider(VisionProvider):
    """Provider palsu: lewat jalur parsing yang sama dengan provider sungguhan."""
    name = "fake"

    def __init__(self, reply=None, exc=None, configured=True):
        self.reply, self.exc, self.configured, self.calls = reply, exc, configured, 0

    def is_configured(self):
        return self.configured

    def model_name(self):
        return "fake-model"

    def _complete(self, image_bytes, media_type):
        self.calls += 1
        if self.exc:
            raise self.exc
        return self.reply


@pytest.fixture(autouse=True)
def _reset_quota(monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "vlm", raising=False)  # test lain mengatur mode sendiri
    quota.reset()
    yield
    quota.reset()


@pytest.fixture()
def pid(client):
    return make_participant(client, ktp_confirmed=False)


def _use(monkeypatch, provider):
    monkeypatch.setattr("app.routes.ktp_scan.get_provider", lambda: provider)
    return provider


def _scan(client, pid, data=None, name="ktp.jpg", ctype="image/jpeg"):
    data = make_image_bytes() if data is None else data
    return client.post("/api/ktp/scan", data={"participant_id": pid}, files={"file": (name, data, ctype)})


# ---------- sukses ----------
def test_valid_scan_returns_structured_result_and_saves_nothing(client, pid, monkeypatch):
    prov = _use(monkeypatch, FakeProvider(vlm_json()))
    r = _scan(client, pid)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["success"] is True and b["saved"] is False
    assert b["data"]["nik"] == VALID_NIK and b["data"]["tanggal_lahir"] == "1995-02-01"
    assert b["data"]["pekerjaan"] == "KARYAWAN SWASTA"
    assert set(b["confidence"]) == set(b["data"]) and b["needs_review"] == []
    assert b["provider"] == "fake" and b["model"] == "fake-model" and prov.calls == 1
    # tidak ada yang disimpan sebelum user konfirmasi
    assert client.db.query(KtpDocument).filter_by(participant_id=pid).count() == 0
    assert client.db.query(Participant).get(pid).nik is None


def test_low_confidence_and_missing_fields(client, pid, monkeypatch):
    _use(monkeypatch, FakeProvider(vlm_json(alamat=("JL X", 0.4), kecamatan=(None, 0.0))))
    b = _scan(client, pid).json()
    assert b["field_status"]["alamat"] == "review" and b["field_status"]["kecamatan"] == "unreadable"
    assert b["data"]["kecamatan"] is None
    assert set(b["needs_review"]) == {"alamat", "kecamatan"}
    assert b["warnings"]


def test_invalid_nik_is_nulled_in_response(client, pid, monkeypatch):
    _use(monkeypatch, FakeProvider(vlm_json(nik="12345")))
    b = _scan(client, pid).json()
    assert b["data"]["nik"] is None and "nik" in b["needs_review"]


def test_confidence_threshold_from_env(client, pid, monkeypatch):
    monkeypatch.setattr(settings, "VLM_CONFIDENCE_THRESHOLD", 0.99, raising=False)
    _use(monkeypatch, FakeProvider(vlm_json(conf=0.95)))
    b = _scan(client, pid).json()
    assert b["confidence_threshold"] == 0.99 and len(b["needs_review"]) == 13


# ---------- file tidak valid ----------
@pytest.mark.parametrize("data,name,ctype,code,status", [
    (b"<html>x</html>", "ktp.jpg", "image/jpeg", "INVALID_FILE_TYPE", 400),
    (b"MZ\x90\x00" + b"\0" * 100, "run.exe", "application/octet-stream", "INVALID_FILE_TYPE", 400),
    (b"", "ktp.jpg", "image/jpeg", "EMPTY_FILE", 400),
    (make_image_bytes("PNG")[:2000], "ktp.png", "image/png", "INVALID_IMAGE", 400),
])
def test_invalid_files_rejected_without_calling_provider(client, pid, monkeypatch, data, name, ctype, code, status):
    prov = _use(monkeypatch, FakeProvider(vlm_json()))
    r = _scan(client, pid, data, name, ctype)
    assert r.status_code == status and r.json()["error_code"] == code
    assert r.json()["can_fill_manually"] is True and prov.calls == 0


def test_oversized_file_413(client, pid, monkeypatch):
    monkeypatch.setattr(settings, "MAX_KTP_FILE_SIZE_MB", 0.01, raising=False)
    prov = _use(monkeypatch, FakeProvider(vlm_json()))
    r = _scan(client, pid, make_image_bytes("PNG", (1200, 800)), "ktp.png", "image/png")
    assert r.status_code == 413 and r.json()["error_code"] == "FILE_TOO_LARGE" and prov.calls == 0


def test_unknown_participant_404(client, monkeypatch):
    _use(monkeypatch, FakeProvider(vlm_json()))
    for bad in ("00000000-0000-0000-0000-000000000000", "bukan-uuid"):
        r = _scan(client, bad)
        assert r.status_code == 404 and r.json()["error_code"] == "PARTICIPANT_NOT_FOUND"


# ---------- kegagalan VLM ----------
@pytest.mark.parametrize("reply,exc,status,code", [
    (None, VisionTimeout(), 504, "VLM_TIMEOUT"),
    (None, VisionUnavailable(), 503, "VLM_UNAVAILABLE"),
    (None, VisionRateLimited(), 429, "VLM_RATE_LIMITED"),
    (None, VisionBadResponse(), 502, "VLM_BAD_RESPONSE"),
    ("ini bukan json", None, 502, "VLM_BAD_RESPONSE"),          # respons malformed dari model
    ('{"fields": ', None, 502, "VLM_BAD_RESPONSE"),
])
def test_provider_failures_are_clean_errors(client, pid, monkeypatch, reply, exc, status, code):
    _use(monkeypatch, FakeProvider(reply, exc))
    r = _scan(client, pid)
    assert r.status_code == status and r.json()["error_code"] == code
    assert r.json()["success"] is False and r.json()["can_fill_manually"] is True


def test_provider_not_configured_503_and_no_quota_used(client, pid, monkeypatch):
    _use(monkeypatch, FakeProvider(vlm_json(), configured=False))
    r = _scan(client, pid)
    assert r.status_code == 503 and r.json()["error_code"] == "VLM_NOT_CONFIGURED"
    _use(monkeypatch, FakeProvider(vlm_json(), exc=VisionNotConfigured("kunci ditolak")))
    assert _scan(client, pid).json()["error_code"] == "VLM_NOT_CONFIGURED"


def test_unexpected_provider_exception_does_not_crash_server(client, pid, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    _use(monkeypatch, FakeProvider(vlm_json(), exc=ZeroDivisionError("boom")))
    c = TestClient(app, raise_server_exceptions=False)
    c.db = client.db
    r = c.post("/api/ktp/scan", data={"participant_id": pid}, files={"file": ("k.jpg", make_image_bytes(), "image/jpeg")})
    assert r.status_code == 500 and r.json()["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "boom" not in r.text and "Traceback" not in r.text


def test_not_a_ktp_422(client, pid, monkeypatch):
    _use(monkeypatch, FakeProvider('{"document_type":"BUKAN_KTP","confidence":0.9,"fields":{},"warnings":[]}'))
    r = _scan(client, pid)
    assert r.status_code == 422 and r.json()["error_code"] == "NOT_A_KTP"


def test_unreadable_ktp_422(client, pid, monkeypatch):
    _use(monkeypatch, FakeProvider('{"document_type":"KTP","confidence":0.1,"fields":{},"warnings":["gambar buram"]}'))
    r = _scan(client, pid)
    assert r.status_code == 422 and r.json()["error_code"] == "KTP_UNREADABLE"


# ---------- pembatasan akses / biaya ----------
def test_per_participant_quota(client, pid, monkeypatch):
    monkeypatch.setattr(settings, "KTP_SCAN_MAX_PER_PARTICIPANT", 2, raising=False)
    prov = _use(monkeypatch, FakeProvider(vlm_json()))
    assert [_scan(client, pid).status_code for _ in range(2)] == [200, 200]
    r = _scan(client, pid)
    assert r.status_code == 429 and r.json()["error_code"] == "SCAN_QUOTA_EXCEEDED" and prov.calls == 2


def test_global_quota(client, pid, monkeypatch):
    monkeypatch.setattr(settings, "KTP_SCAN_GLOBAL_MAX_PER_WINDOW", 1, raising=False)
    _use(monkeypatch, FakeProvider(vlm_json()))
    assert _scan(client, pid).status_code == 200
    assert _scan(client, make_participant(client, ktp_confirmed=False, nama="Lain")).status_code == 429


def test_invalid_files_do_not_consume_quota(client, pid, monkeypatch):
    monkeypatch.setattr(settings, "KTP_SCAN_MAX_PER_PARTICIPANT", 1, raising=False)
    _use(monkeypatch, FakeProvider(vlm_json()))
    for _ in range(3):
        assert _scan(client, pid, b"<html>", "x.jpg").status_code == 400
    assert _scan(client, pid).status_code == 200


def test_ip_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "KTP_SCAN_RATE_LIMIT", "2/minute", raising=False)
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [_scan(client, "00000000-0000-0000-0000-000000000000").status_code for _ in range(3)]
        assert codes == [404, 404, 429]
    finally:
        limiter.enabled = False
        limiter.reset()


# ---------- privasi ----------
def test_no_ktp_data_in_logs(client, pid, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    _use(monkeypatch, FakeProvider(vlm_json()))
    assert _scan(client, pid).status_code == 200
    _use(monkeypatch, FakeProvider("rusak { json " + VALID_NIK))
    assert _scan(client, pid).status_code == 502
    logs = "\n".join(r.getMessage() for r in caplog.records)
    assert VALID_NIK not in logs and "BUDI SANTOSO" not in logs and "base64" not in logs


def test_error_response_never_echoes_ktp_content(client, pid, monkeypatch):
    _use(monkeypatch, FakeProvider("rusak { json " + VALID_NIK + " BUDI SANTOSO"))
    r = _scan(client, pid)
    assert VALID_NIK not in r.text and "BUDI" not in r.text


# ---------- alur lengkap: scan -> user periksa -> konfirmasi (+ fallback manual) ----------
CONFIRM = dict(nik=VALID_NIK, nama="BUDI SANTOSO", tempat_lahir="BOGOR", tanggal_lahir="01-02-1995",
               jenis_kelamin="LAKI-LAKI", alamat="JL MERDEKA NO 1", rt_rw="001/002", kelurahan="SUKAJADI",
               kecamatan="BOGOR BARAT", agama="ISLAM", status_perkawinan="KAWIN",
               pekerjaan_ktp="KARYAWAN SWASTA", kewarganegaraan="WNI")


def test_scan_then_user_confirm_saves_data(client, pid, monkeypatch):
    _use(monkeypatch, FakeProvider(vlm_json()))
    assert _scan(client, pid).status_code == 200
    assert client.get(f"/api/participants/{pid}").json()["ktp_confirmed"] is False
    r = client.post("/api/ocr/ktp/confirm", json={"participant_id": pid, "scan_provider": "anthropic",
                                                   "scan_confidence": 97, **CONFIRM})
    assert r.status_code == 200, r.text
    assert client.get(f"/api/participants/{pid}").json()["ktp_confirmed"] is True
    doc = client.db.query(KtpDocument).filter_by(participant_id=pid).one()
    assert doc.ocr_provider == "anthropic" and doc.ocr_confidence == 97 and doc.file_path is None
    assert doc.corrected_by_user is True and doc.ocr_raw_text is None  # tanpa gambar & tanpa JSON mentah AI


def test_manual_fallback_when_ai_fails(client, pid, monkeypatch):
    """AI gagal -> user tetap bisa isi manual dan konfirmasi."""
    _use(monkeypatch, FakeProvider(exc=VisionUnavailable()))
    assert _scan(client, pid).status_code == 503
    r = client.post("/api/ocr/ktp/confirm", json={"participant_id": pid, **CONFIRM})
    assert r.status_code == 200, r.text
    assert client.get(f"/api/participants/{pid}").json()["ktp_confirmed"] is True
    assert client.db.query(KtpDocument).filter_by(participant_id=pid).one().ocr_provider == "manual"


def test_confirm_still_validates_fields(client, pid):
    r = client.post("/api/ocr/ktp/confirm", json={"participant_id": pid, **{**CONFIRM, "nik": "123"}})
    assert r.status_code == 422


def test_legacy_confirm_with_existing_document_still_works(client, pid):
    client.db.add(KtpDocument(participant_id=pid, ocr_provider="vlm"))
    client.db.commit()
    r = client.post("/api/ocr/ktp/confirm", json={"participant_id": pid, **CONFIRM})
    assert r.status_code == 200
    assert client.db.query(KtpDocument).filter_by(participant_id=pid).count() == 1


def test_auto_confirm_is_off_by_default():
    assert settings.VLM_AUTO_CONFIRM is False


def test_endpoint_documented_in_swagger(client):
    spec = client.get("/openapi.json").json()
    op = spec["paths"]["/api/ktp/scan"]["post"]
    assert {"200", "400", "413", "422", "429", "500"} <= set(op["responses"])
    assert "KtpScanResponse" in spec["components"]["schemas"]


# ---------- Tesseract (gratis/offline) & fallback ----------
class FakeTesseract(FakeProvider):
    name = "tesseract"


def _use_chain(monkeypatch, vlm, tess, mode):
    monkeypatch.setattr(settings, "OCR_PROVIDER", mode, raising=False)
    monkeypatch.setattr("app.routes.ktp_scan.get_provider", lambda: vlm)
    monkeypatch.setattr("app.routes.ktp_scan.TesseractProvider", lambda: tess)


def test_mode_tesseract_never_calls_vlm(client, pid, monkeypatch):
    vlm, tess = FakeProvider(vlm_json()), FakeTesseract(vlm_json(conf=0.5))
    _use_chain(monkeypatch, vlm, tess, "tesseract")
    b = _scan(client, pid).json()
    assert b["provider"] == "tesseract" and b["fallback_used"] is False and vlm.calls == 0
    assert len(b["needs_review"]) == 13  # confidence 0.5 < threshold -> semua wajib diperiksa


def test_unknown_mode_like_local_behaves_as_tesseract(client, pid, monkeypatch):
    vlm, tess = FakeProvider(vlm_json()), FakeTesseract(vlm_json(conf=0.5))
    _use_chain(monkeypatch, vlm, tess, "local")
    assert _scan(client, pid).json()["provider"] == "tesseract" and vlm.calls == 0


@pytest.mark.parametrize("vlm", [
    FakeProvider(exc=VisionUnavailable()), FakeProvider(exc=VisionTimeout()),
    FakeProvider(vlm_json(), configured=False), FakeProvider("bukan json"),
])
def test_auto_falls_back_to_tesseract_when_vlm_fails(client, pid, monkeypatch, vlm):
    _use_chain(monkeypatch, vlm, FakeTesseract(vlm_json(conf=0.5)), "auto")
    r = _scan(client, pid)
    assert r.status_code == 200, r.text
    assert r.json()["provider"] == "tesseract" and r.json()["fallback_used"] is True
    assert "Tesseract" in r.json()["message"]


def test_auto_uses_vlm_when_it_works(client, pid, monkeypatch):
    tess = FakeTesseract(vlm_json())
    _use_chain(monkeypatch, FakeProvider(vlm_json()), tess, "auto")
    b = _scan(client, pid).json()
    assert b["provider"] == "fake" and b["fallback_used"] is False and tess.calls == 0


def test_auto_both_fail_returns_vlm_error(client, pid, monkeypatch):
    _use_chain(monkeypatch, FakeProvider(exc=VisionTimeout()), FakeTesseract(exc=VisionBadResponse()), "auto")
    r = _scan(client, pid)
    assert r.status_code == 504 and r.json()["error_code"] == "VLM_TIMEOUT"


def test_tesseract_not_installed_gives_clean_error(client, pid, monkeypatch):
    _use_chain(monkeypatch, FakeProvider(), FakeTesseract(vlm_json(), configured=False), "tesseract")
    r = _scan(client, pid)
    assert r.status_code == 503 and r.json()["error_code"] == "VLM_NOT_CONFIGURED"


def test_tesseract_does_not_consume_vlm_quota(client, pid, monkeypatch):
    monkeypatch.setattr(settings, "KTP_SCAN_MAX_PER_PARTICIPANT", 1, raising=False)
    _use_chain(monkeypatch, FakeProvider(vlm_json()), FakeTesseract(vlm_json(conf=0.5)), "tesseract")
    assert [_scan(client, pid).status_code for _ in range(3)] == [200, 200, 200]
