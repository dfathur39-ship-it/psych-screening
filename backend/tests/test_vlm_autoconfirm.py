"""Auto-confirm: lengkap -> langsung confirmed, tidak lengkap -> manual."""
from tests.conftest import dob
from app.routes.ocr import _is_complete_for_auto_confirm
from app.services.ocr_service import OcrExtraction


def _full(**over):
    base = dict(
        raw_text="x", nik="3171234567890123", nama="Flow Tester",
        tempat_lahir="BOGOR", tanggal_lahir=dob(30), jenis_kelamin="LAKI-LAKI",
        alamat="JL MERDEKA NO 1", rt_rw="001/002", kelurahan="SUKAJADI",
        kecamatan="BOGOR BARAT", agama="ISLAM", status_perkawinan="KAWIN",
        pekerjaan_ktp="KARYAWAN SWASTA", kewarganegaraan="WNI",
        confidence=100, provider="vlm",
    )
    base.update(over)
    return OcrExtraction(**base)


def test_lengkap_bisa_auto_confirm(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "VLM_AUTO_CONFIRM_MIN_CONFIDENCE", 80, raising=False)
    ok, _ = _is_complete_for_auto_confirm(_full())
    assert ok is True


def test_tidak_lengkap_gagal():
    ok, reason = _is_complete_for_auto_confirm(_full(nama=None))
    assert ok is False and "field_kosong" in reason


def test_nik_invalid_gagal():
    ok, reason = _is_complete_for_auto_confirm(_full(nik="123"))
    assert ok is False and reason == "nik_tidak_valid"


def test_tanggal_invalid_gagal():
    ok, reason = _is_complete_for_auto_confirm(_full(tanggal_lahir="1995/02/01"))
    assert ok is False and reason == "tanggal_lahir_tidak_valid"


def test_confidence_rendah_gagal(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "VLM_AUTO_CONFIRM_MIN_CONFIDENCE", 80, raising=False)
    ok, reason = _is_complete_for_auto_confirm(_full(confidence=50))
    assert ok is False and reason.startswith("confidence_rendah")


def test_route_auto_confirm_lengkap(client, monkeypatch, tmp_path):
    """POST /api/ocr/ktp dengan hasil VLM lengkap -> ktp langsung confirmed."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "OCR_PROVIDER", "auto", raising=False)
    monkeypatch.setattr(settings, "VLM_AUTO_CONFIRM", True, raising=False)
    monkeypatch.setattr(settings, "VLM_AUTO_CONFIRM_MIN_CONFIDENCE", 80, raising=False)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path), raising=False)

    from tests.conftest import make_participant
    pid = make_participant(client, ktp_confirmed=False)

    ext = _full()
    monkeypatch.setattr("app.routes.ocr.run_ocr_on_image", lambda _p, provider_override=None: ext)

    with open(tmp_path / "k.jpg", "wb") as f:
        f.write(b"\xff\xd8\xff fake")
    with open(tmp_path / "k.jpg", "rb") as f:
        r = client.post("/api/ocr/ktp?provider=auto&auto_confirm=true",
                        files={"file": ("k.jpg", f, "image/jpeg")},
                        data={"participant_id": pid})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["auto_confirmed"] is True
    assert body["ktp_confirmed"] is True
    assert body["ocr_provider"] == "vlm"

    # profil harus sudah confirmed -> bisa langsung skrining tanpa halaman periksa
    p = client.get(f"/api/participants/{pid}").json()
    assert p["ktp_confirmed"] is True


def test_route_tidak_lengkap_tetap_manual(client, monkeypatch, tmp_path):
    from app.core.config import settings
    monkeypatch.setattr(settings, "OCR_PROVIDER", "auto", raising=False)
    monkeypatch.setattr(settings, "VLM_AUTO_CONFIRM", True, raising=False)
    monkeypatch.setattr(settings, "VLM_AUTO_CONFIRM_MIN_CONFIDENCE", 80, raising=False)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path), raising=False)

    from tests.conftest import make_participant
    pid = make_participant(client, ktp_confirmed=False)

    ext = _full(nama=None, confidence=30)  # tidak lengkap
    monkeypatch.setattr("app.routes.ocr.run_ocr_on_image", lambda _p, provider_override=None: ext)

    with open(tmp_path / "k2.jpg", "wb") as f:
        f.write(b"\xff\xd8\xff fake")
    with open(tmp_path / "k2.jpg", "rb") as f:
        r = client.post("/api/ocr/ktp?provider=auto&auto_confirm=true",
                        files={"file": ("k2.jpg", f, "image/jpeg")},
                        data={"participant_id": pid})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["auto_confirmed"] is False
    assert body["ktp_confirmed"] is False
