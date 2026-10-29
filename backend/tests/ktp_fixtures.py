"""Helper bersama untuk test fitur scan KTP (tanpa API berbayar)."""
import io
import json
import random

from PIL import Image

VALID_NIK = "3171230102950001"  # DDMMYY di digit 7-12 = 010295 -> cocok dengan 1995-02-01


def make_image_bytes(fmt="JPEG", size=(900, 570), mode="RGB") -> bytes:
    rnd = random.Random(7)
    img = Image.new(mode, size, (235, 235, 235) if mode == "RGB" else 200)
    px = img.load()
    for _ in range(4000):  # noise supaya bukan gambar kosong
        x, y = rnd.randrange(size[0]), rnd.randrange(size[1])
        px[x, y] = (20, 20, 20) if mode == "RGB" else 20
    out = io.BytesIO()
    img.save(out, format=fmt)
    return out.getvalue()


def vlm_json(conf=0.97, **override) -> str:
    """JSON jawaban VLM yang valid. override: nama_field=(value, confidence) atau nilai saja."""
    base = {
        "nik": VALID_NIK, "nama": "BUDI SANTOSO", "tempat_lahir": "BOGOR", "tanggal_lahir": "1995-02-01",
        "jenis_kelamin": "LAKI-LAKI", "alamat": "JL MERDEKA NO 1", "rt_rw": "001/002",
        "kelurahan": "SUKAJADI", "kecamatan": "BOGOR BARAT", "agama": "ISLAM",
        "status_perkawinan": "KAWIN", "pekerjaan": "KARYAWAN SWASTA", "kewarganegaraan": "WNI",
    }
    fields = {}
    for k, v in base.items():
        fields[k] = {"value": v, "confidence": conf}
    for k, v in override.items():
        if isinstance(v, tuple):
            fields[k] = {"value": v[0], "confidence": v[1]}
        else:
            fields[k] = {"value": v, "confidence": conf}
    return json.dumps({"document_type": "KTP", "confidence": conf, "fields": fields, "warnings": []})
