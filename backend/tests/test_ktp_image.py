"""Validasi + preprocessing gambar KTP."""
import io

import pytest
from PIL import Image

from app.core.config import settings
from app.services import ktp_image
from app.services.ktp_image import ImageValidationError, prepare_image
from tests.ktp_fixtures import make_image_bytes


@pytest.mark.parametrize("fmt,mime,fname", [
    ("JPEG", "image/jpeg", "ktp.jpg"), ("PNG", "image/png", "ktp.png"), ("WEBP", "image/webp", "ktp.webp"),
])
def test_valid_image_formats(fmt, mime, fname):
    prepared = prepare_image(make_image_bytes(fmt), fname, mime)
    assert prepared.media_type == "image/jpeg" and prepared.preprocessed is True
    Image.open(io.BytesIO(prepared.data)).verify()


def test_large_image_is_downscaled():
    prepared = prepare_image(make_image_bytes("JPEG", (3200, 2000)), "k.jpg", "image/jpeg")
    assert max(prepared.width, prepared.height) <= settings.KTP_VLM_IMAGE_MAX_SIDE_PX


def test_exif_orientation_is_applied():
    img = Image.new("RGB", (800, 400), (200, 200, 200))
    exif = img.getexif()
    exif[0x0112] = 6  # rotate 90 CW saat ditampilkan
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=exif)
    prepared = prepare_image(out.getvalue(), "k.jpg", "image/jpeg")
    assert (prepared.width, prepared.height) == (400, 800)


def test_rgba_png_is_flattened():
    prepared = prepare_image(_rgba_png(), "k.png", "image/png")
    assert prepared.media_type == "image/jpeg"


def _rgba_png() -> bytes:
    out = io.BytesIO()
    Image.new("RGBA", (600, 400), (255, 0, 0, 120)).save(out, format="PNG")
    return out.getvalue()


@pytest.mark.parametrize("payload,name,ctype", [
    (b"<html><script>alert(1)</script></html>", "ktp.jpg", "image/jpeg"),   # HTML menyamar jadi jpg
    (b"MZ\x90\x00" + b"\x00" * 200, "ktp.png", "image/png"),                 # executable
    (b"#!/bin/sh\nrm -rf /\n", "ktp.jpg", "image/jpeg"),                     # script
    (b"%PDF-1.4 fake", "ktp.jpg", "image/jpeg"),
    (b"just some text", "ktp.webp", "image/webp"),
])
def test_dangerous_or_unknown_content_rejected(payload, name, ctype):
    with pytest.raises(ImageValidationError) as e:
        prepare_image(payload, name, ctype)
    assert e.value.code == "INVALID_FILE_TYPE" and e.value.http_status == 400


@pytest.mark.parametrize("name,ctype", [("ktp.exe", "image/jpeg"), ("ktp.html", "image/jpeg"), ("ktp.svg", "image/svg+xml")])
def test_bad_extension_or_declared_mime_rejected(name, ctype):
    with pytest.raises(ImageValidationError) as e:
        prepare_image(make_image_bytes(), name, ctype)
    assert e.value.code == "INVALID_FILE_TYPE"


def test_empty_file_rejected():
    with pytest.raises(ImageValidationError) as e:
        prepare_image(b"", "ktp.jpg", "image/jpeg")
    assert e.value.code == "EMPTY_FILE"


def test_oversized_file_rejected_413(monkeypatch):
    monkeypatch.setattr(settings, "MAX_KTP_FILE_SIZE_MB", 0.01, raising=False)  # ~10 KB
    with pytest.raises(ImageValidationError) as e:
        prepare_image(make_image_bytes("PNG", (900, 570)), "ktp.png", "image/png")
    assert e.value.http_status == 413 and e.value.code == "FILE_TOO_LARGE"


def test_corrupted_image_rejected():
    good = make_image_bytes("PNG")
    corrupted = good[: len(good) // 2]  # header valid, isi terpotong
    with pytest.raises(ImageValidationError) as e:
        prepare_image(corrupted, "ktp.png", "image/png")
    assert e.value.code == "INVALID_IMAGE"


def test_valid_magic_but_garbage_body_rejected():
    with pytest.raises(ImageValidationError) as e:
        prepare_image(b"\xff\xd8\xff" + b"\x00" * 500, "ktp.jpg", "image/jpeg")
    assert e.value.code == "INVALID_IMAGE"


def test_too_small_rejected():
    with pytest.raises(ImageValidationError) as e:
        prepare_image(make_image_bytes("JPEG", (120, 80)), "ktp.jpg", "image/jpeg")
    assert e.value.code == "IMAGE_TOO_SMALL"


def test_dimensions_too_large_rejected(monkeypatch):
    monkeypatch.setattr(settings, "KTP_MAX_IMAGE_SIDE_PX", 1000, raising=False)
    with pytest.raises(ImageValidationError) as e:
        prepare_image(make_image_bytes("JPEG", (1500, 900)), "ktp.jpg", "image/jpeg")
    assert e.value.code == "IMAGE_DIMENSIONS_TOO_LARGE"


def test_preprocess_failure_falls_back_to_original(monkeypatch):
    def boom(_data):
        raise RuntimeError("boom")
    monkeypatch.setattr(ktp_image, "_preprocess", boom)
    original = make_image_bytes("JPEG")
    prepared = prepare_image(original, "ktp.jpg", "image/jpeg")
    assert prepared.preprocessed is False and prepared.data == original and prepared.media_type == "image/jpeg"


def test_preprocess_can_be_disabled(monkeypatch):
    monkeypatch.setattr(settings, "KTP_PREPROCESS", False, raising=False)
    original = make_image_bytes("PNG")
    prepared = prepare_image(original, "ktp.png", "image/png")
    assert prepared.preprocessed is False and prepared.data == original and prepared.media_type == "image/png"
