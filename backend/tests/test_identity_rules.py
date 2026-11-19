"""Aturan identitas: satu nama satu akun, data diri harus sama dengan KTP, NIK unik."""
from app.models.models import KtpDocument
from tests.conftest import dob

BASE = {"nama": "Siti Rahma", "usia": 28, "jabatan": "Staff", "no_hp": "081111111111", "email": "siti@example.com"}
KTP = dict(nik="3171000000000001", nama="Siti Rahma", tempat_lahir="BOGOR", jenis_kelamin="PEREMPUAN",
           alamat="JL A", rt_rw="001/002", kelurahan="X", kecamatan="Y", agama="ISLAM",
           status_perkawinan="KAWIN", pekerjaan_ktp="KARYAWAN", kewarganegaraan="WNI")


def _reg(client, **over):
    return client.post("/api/participants", json={**BASE, **over})


def _with_ktp_doc(db, pid):
    db.add(KtpDocument(participant_id=pid))
    db.commit()


def test_same_data_enters_same_account(client):
    a = _reg(client)
    b = _reg(client)
    assert a.status_code == 201 and b.status_code == 200
    assert a.json()["id"] == b.json()["id"]


def test_same_data_with_different_case_and_spaces_is_same_account(client):
    a = _reg(client)
    b = _reg(client, nama="  siti   RAHMA ", email="SITI@example.com", no_hp="+6281111111111")
    assert b.status_code == 200 and a.json()["id"] == b.json()["id"]


def test_same_name_different_data_is_rejected(client):
    _reg(client)
    for over in ({"email": "lain@example.com"}, {"no_hp": "082222222222"}, {"usia": 40}, {"jabatan": "Manager"}):
        r = _reg(client, **over)
        assert r.status_code == 409 and r.json()["error_code"] == "NAMA_SUDAH_TERDAFTAR", over


def test_different_name_creates_new_account(client):
    a = _reg(client)
    b = _reg(client, nama="Siti Rahmawati", email="x@example.com")
    assert b.status_code == 201 and a.json()["id"] != b.json()["id"]


def test_ktp_name_must_match(client, db):
    pid = _reg(client).json()["id"]
    _with_ktp_doc(db, pid)
    r = client.post("/api/ocr/ktp/confirm", json={"participant_id": pid, **KTP, "nama": "Orang Lain", "tanggal_lahir": dob(28)})
    assert r.status_code == 400 and r.json()["error_code"] == "NAMA_TIDAK_SAMA"


def test_ktp_age_must_match(client, db):
    pid = _reg(client).json()["id"]
    _with_ktp_doc(db, pid)
    r = client.post("/api/ocr/ktp/confirm", json={"participant_id": pid, **KTP, "tanggal_lahir": dob(35)})
    assert r.status_code == 400 and r.json()["error_code"] == "USIA_TIDAK_SAMA"
    r = client.post("/api/ocr/ktp/confirm", json={"participant_id": pid, **KTP, "tanggal_lahir": dob(28)})
    assert r.status_code == 200, r.text


def test_future_birth_date_rejected(client, db):
    pid = _reg(client).json()["id"]
    _with_ktp_doc(db, pid)
    r = client.post("/api/ocr/ktp/confirm", json={"participant_id": pid, **KTP, "tanggal_lahir": "01-01-2999"})
    assert r.status_code == 400 and r.json()["error_code"] == "TANGGAL_LAHIR_TIDAK_VALID"


def test_nik_cannot_be_used_by_two_accounts(client, db):
    a = _reg(client).json()["id"]
    b = _reg(client, nama="Budi Hartono", usia=28, email="b@example.com").json()["id"]
    for pid in (a, b):
        _with_ktp_doc(db, pid)
    ok = client.post("/api/ocr/ktp/confirm", json={"participant_id": a, **KTP, "tanggal_lahir": dob(28)})
    assert ok.status_code == 200, ok.text
    dup = client.post("/api/ocr/ktp/confirm", json={"participant_id": b, **KTP, "nama": "Budi Hartono", "tanggal_lahir": dob(28)})
    assert dup.status_code == 409 and dup.json()["error_code"] == "NIK_SUDAH_TERDAFTAR"


def test_export_has_time_columns_and_pdf(client, db, admin_token):
    from tests.conftest import make_participant
    pid = make_participant(client)
    h = {"Authorization": f"Bearer {admin_token}"}
    csv = client.get("/api/admin/export/csv", headers=h)
    assert csv.status_code == 200
    header = csv.text.splitlines()[0]
    assert "Mulai" in header and "Selesai" in header and "Durasi" in header
    pdf = client.get("/api/admin/export/pdf", headers=h)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert client.get("/api/admin/export/pdf").status_code == 401
    assert pid
