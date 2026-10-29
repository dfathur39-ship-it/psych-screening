def test_create_participant_success(client):
    r = client.post("/api/participants", json={
        "nama": "Test User", "usia": 25, "jabatan": "Programmer", "no_hp": "081234567890", "email": "user@example.com",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["nama"] == "Test User"
    assert body["nik_masked"] is None
    assert body["email"] == "user@example.com"
    assert body["ktp_confirmed"] is False


def test_create_participant_invalid_age(client):
    r = client.post("/api/participants", json={
        "nama": "Test User", "usia": 10, "jabatan": "Programmer", "no_hp": "081234567890", "email": "user@example.com",
    })
    assert r.status_code == 422


def test_create_participant_missing_field(client):
    r = client.post("/api/participants", json={
        "nama": "Test User", "usia": 25, "no_hp": "081234567890", "email": "user@example.com",
    })
    assert r.status_code == 422


def test_create_participant_free_text_jabatan_accepted(client):
    r = client.post("/api/participants", json={
        "nama": "Test User", "usia": 25,         "jabatan": "Senior Blockchain Evangelist Ninja", "no_hp": "081234567890", "email": "user@example.com",
    })
    assert r.status_code == 201


# ---------- KTP confirmation: every field is mandatory ----------
KTP_FULL = {
    "nik": "3171234567890123", "nama": "Budi Santoso", "tempat_lahir": "Bogor",
    "tanggal_lahir": "01-02-1995", "jenis_kelamin": "LAKI-LAKI", "alamat": "Jl. Merdeka No. 1",
    "rt_rw": "001/002", "kelurahan": "Sukajadi", "kecamatan": "Bogor Barat", "agama": "Islam",
    "status_perkawinan": "Kawin", "pekerjaan_ktp": "Karyawan Swasta", "kewarganegaraan": "WNI",
}


def _participant_with_ktp(client, db):
    from app.models.models import KtpDocument
    r = client.post("/api/participants", json={
        "nama": "Budi", "usia": 30, "jabatan": "Staff", "no_hp": "081234567890", "email": "user@example.com"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    db.add(KtpDocument(participant_id=pid))
    db.commit()
    return pid


def test_ktp_confirm_accepts_complete_data(client, db):
    pid = _participant_with_ktp(client, db)
    r = client.post("/api/ocr/ktp/confirm", json={"participant_id": pid, **KTP_FULL})
    assert r.status_code == 200, r.text
    assert r.json()["nik_masked"] == "3171************"


def test_ktp_confirm_rejects_any_missing_field(client, db):
    pid = _participant_with_ktp(client, db)
    for field in KTP_FULL:
        body = {"participant_id": pid, **KTP_FULL}
        del body[field]
        assert client.post("/api/ocr/ktp/confirm", json=body).status_code == 422, field
        body[field] = "   "
        assert client.post("/api/ocr/ktp/confirm", json=body).status_code == 422, f"blank {field}"


def test_ktp_confirm_validates_formats(client, db):
    pid = _participant_with_ktp(client, db)
    bad_nik = {"participant_id": pid, **KTP_FULL, "nik": "12345"}
    bad_date = {"participant_id": pid, **KTP_FULL, "tanggal_lahir": "1995-02-01"}
    assert client.post("/api/ocr/ktp/confirm", json=bad_nik).status_code == 422
    assert client.post("/api/ocr/ktp/confirm", json=bad_date).status_code == 422


def test_participant_no_longer_accepts_or_returns_divisi(client):
    r = client.post("/api/participants", json={
        "nama": "Budi", "usia": 30, "jabatan": "Staff", "no_hp": "081234567890", "email": "user@example.com"})
    assert r.status_code == 201 and "divisi" not in r.json()


# ---------- email ----------
def _body(**over):
    return {"nama": "Test User", "usia": 25, "jabatan": "Programmer", "no_hp": "081234567890",
            "email": "user@example.com", **over}


def test_email_is_required(client):
    body = _body()
    del body["email"]
    assert client.post("/api/participants", json=body).status_code == 422


def test_email_must_be_valid(client):
    for bad in ["", "bukan-email", "a@", "@example.com", "a b@example.com"]:
        assert client.post("/api/participants", json=_body(email=bad)).status_code == 422, bad


def test_email_is_normalized(client):
    r = client.post("/api/participants", json=_body(email="  Budi.Santoso@Example.COM "))
    assert r.status_code == 201
    assert r.json()["email"] == "budi.santoso@example.com"


# ---------- profile ----------
def test_get_profile_reports_ktp_and_session_state(client, db):
    pid = client.post("/api/participants", json=_body()).json()["id"]
    r = client.get(f"/api/participants/{pid}")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "user@example.com" and body["ktp_confirmed"] is False
    assert body["in_progress_session_id"] is None and body["completed_session_id"] is None

    from app.models.models import KtpDocument
    db.add(KtpDocument(participant_id=pid))
    db.commit()
    assert client.post("/api/ocr/ktp/confirm", json={"participant_id": pid, **KTP_FULL}).status_code == 200
    body = client.get(f"/api/participants/{pid}").json()
    assert body["ktp_confirmed"] is True and body["nik_masked"] == "3171************"


def test_get_profile_unknown_or_malformed_id_is_404(client):
    assert client.get("/api/participants/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/api/participants/bukan-uuid").status_code == 404
