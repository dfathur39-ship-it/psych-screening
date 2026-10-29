from app.services.ocr_service import parse_ktp_text

SAMPLE = """PROVINSI DKI JAKARTA
NIK : 3171234567890123
Nama : BUDI SANTOSO
Tempat/Tgl Lahir : BOGOR, 01-02-1995
Jenis Kelamin : LAKI-LAKI
Alamat : JL MERDEKA NO 1
RT/RW : 001/002
Kel/Desa : SUKAJADI
Kecamatan : BOGOR BARAT
Agama : ISLAM
Status Perkawinan : KAWIN
Pekerjaan : KARYAWAN SWASTA
Kewarganegaraan : WNI
"""


def test_parses_all_fields():
    r = parse_ktp_text(SAMPLE)
    assert r.nik == "3171234567890123"
    assert r.nama == "BUDI SANTOSO"
    assert r.kecamatan == "BOGOR BARAT"
    assert r.agama == "ISLAM"
    assert r.status_perkawinan == "KAWIN"
    assert r.kewarganegaraan == "WNI"


def test_kelurahan_is_not_confused_with_jenis_kelamin():
    r = parse_ktp_text(SAMPLE)
    assert r.jenis_kelamin == "LAKI-LAKI"
    assert r.kelurahan == "SUKAJADI"


def test_missing_kelurahan_stays_empty_instead_of_grabbing_kelamin():
    r = parse_ktp_text("Jenis Kelamin : PEREMPUAN\nNama : SITI")
    assert r.kelurahan is None


def test_empty_text_gives_empty_result():
    r = parse_ktp_text("")
    assert r.nik is None and r.confidence == 0
