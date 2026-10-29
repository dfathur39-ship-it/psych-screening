"""TesseractProvider dengan Tesseract sungguhan (di-skip bila tidak terpasang)."""
import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.vision.tesseract_provider import TesseractProvider

pytestmark = pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract tidak terpasang")

LINES = ["PROVINSI DKI JAKARTA", "NIK : 3171230102950001", "Nama : BUDI SANTOSO",
         "Tempat/Tgl Lahir : BOGOR, 01-02-1995", "Jenis Kelamin : LAKI-LAKI", "Alamat : JL MERDEKA NO 1",
         "RT/RW : 001/002", "Kel/Desa : SUKAJADI", "Kecamatan : BOGOR BARAT", "Agama : ISLAM",
         "Status Perkawinan : KAWIN", "Pekerjaan : KARYAWAN SWASTA", "Kewarganegaraan : WNI"]


def _card() -> bytes:
    img = Image.new("RGB", (1100, 900), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    for i, line in enumerate(LINES):
        d.text((40, 30 + i * 62), line, fill="black", font=font)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def test_real_tesseract_extracts_fields_and_splits_birth():
    r = TesseractProvider().extract_ktp(_card(), "image/png")
    assert r.provider == "tesseract" and r.fields["nik"].value == "3171230102950001"
    assert r.fields["tanggal_lahir"].value == "01-02-1995"
    assert r.fields["tempat_lahir"].value == "BOGOR"
    assert r.fields["nama"].value == "BUDI SANTOSO"
    assert r.fields["nama"].confidence < 0.8


def test_tidy_values_cleans_typical_ocr_junk():
    from app.services.vision.tesseract_provider import tidy_values
    v = tidy_values({"jenis_kelamin": "PEREMPUAN Gol. Darah : 8", "agama": "ISLAM ba", "status_perkawinan": "KAWIN “4",
                     "kecamatan": "KALIDERES |", "kewarganegaraan": "WNI JAKARTA BARAT", "rt_rw": "A", "nama": None},
                    "RT/RW : 007/008")
    assert v["jenis_kelamin"] == "PEREMPUAN" and v["agama"] == "ISLAM" and v["status_perkawinan"] == "KAWIN"
    assert v["kecamatan"] == "KALIDERES" and v["kewarganegaraan"] == "WNI" and v["rt_rw"] == "007/008"
    assert v["nama"] is None
