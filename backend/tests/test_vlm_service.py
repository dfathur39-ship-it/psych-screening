"""Tests untuk VLM service + dispatcher fallback (tanpa API key asli / tanpa Tesseract)."""
import json

from app.services import vlm_service
from app.services import ocr_service


def _fake_settings(tmp_path, monkeypatch, ocr_provider="auto",
                    base="https://fake.local/v1", key="k", model="m"):
    monkeypatch.setenv("OCR_PROVIDER", ocr_provider)
    monkeypatch.setenv("VLM_BASE_URL", base)
    monkeypatch.setenv("VLM_API_KEY", key)
    monkeypatch.setenv("VLM_MODEL", model)
    # reset cached settings
    from app.core import config as cfg
    cfg.get_settings.cache_clear()
    import importlib
    importlib.reload(cfg)
    monkeypatch.setattr("app.core.config.settings", cfg.get_settings(), raising=False)
    return cfg.settings


def test_parse_model_json_toleran_fence():
    raw = '```json\n{"nik":"3171234567890123","nama":"BUDI"}\n```'
    assert vlm_service._parse_model_json(raw)["nik"] == "3171234567890123"


def test_parse_model_json_non_json():
    assert vlm_service._parse_model_json("maaf tidak bisa") == {}


def test_nik_invalid_dinullkan(monkeypatch, tmp_path):
    """Model ngarang NIK pendek -> harus jadi None, bukan dipercaya."""
    import app.services.vlm_service as vs

    monkeypatch.setattr(vs, "is_vlm_configured", lambda: True)

    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": json.dumps({"nik": "123", "nama": "BUDI"})}}]}

    import httpx
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResp())
    # fake settings
    from app.core.config import settings
    monkeypatch.setattr(settings, "VLM_BASE_URL", "https://x/v1", raising=False)
    monkeypatch.setattr(settings, "VLM_API_KEY", "k", raising=False)
    monkeypatch.setattr(settings, "VLM_MODEL", "m", raising=False)
    monkeypatch.setattr(settings, "VLM_TIMEOUT_S", 5, raising=False)

    img = tmp_path / "ktp.jpg"
    img.write_bytes(b"\xff\xd8\xff fake")
    r = vs.extract_ktp_with_vlm(str(img))
    assert r.fields["nik"] is None
    assert r.fields["nama"] == "BUDI"


def test_auto_fallback_ke_tesseract_saat_vlm_gagal(monkeypatch, tmp_path):
    from app.core.config import settings
    monkeypatch.setattr(settings, "OCR_PROVIDER", "auto", raising=False)
    monkeypatch.setattr("app.services.vlm_service.is_vlm_configured", lambda: True)

    def _boom(_path):
        raise RuntimeError("boom")
    monkeypatch.setattr("app.services.vlm_service.extract_ktp_with_vlm", _boom)

    fake = ocr_service.OcrExtraction(raw_text="NIK : 3171234567890123", nik="3171234567890123",
                                     nama="BUDI", confidence=15)
    monkeypatch.setattr(ocr_service, "run_tesseract_on_image", lambda _p: fake)

    r = ocr_service.run_ocr_on_image("dummy.jpg")
    assert r.provider == "tesseract"
    assert r.fallback_used is True


def test_auto_tanpa_config_langsung_tesseract(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "OCR_PROVIDER", "auto", raising=False)
    monkeypatch.setattr("app.services.vlm_service.is_vlm_configured", lambda: False)
    fake = ocr_service.OcrExtraction(raw_text="x", confidence=0)
    monkeypatch.setattr(ocr_service, "run_tesseract_on_image", lambda _p: fake)
    r = ocr_service.run_ocr_on_image("dummy.jpg")
    assert r.fallback_reason == "vlm_not_configured"


def test_mode_vlm_murni_gagal_tidak_fallback_diam(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "OCR_PROVIDER", "vlm", raising=False)
    monkeypatch.setattr("app.services.vlm_service.is_vlm_configured", lambda: True)

    def _boom(_path):
        raise RuntimeError("timeout")
    monkeypatch.setattr("app.services.vlm_service.extract_ktp_with_vlm", _boom)
    r = ocr_service.run_ocr_on_image("dummy.jpg", provider_override="vlm")
    assert r.provider == "vlm" and r.confidence == 0 and r.fallback_used is False
