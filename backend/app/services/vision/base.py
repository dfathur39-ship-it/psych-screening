"""
Abstraksi provider VLM untuk ekstraksi KTP.

    VisionProvider
        +-- AnthropicVisionProvider   (Claude Vision, SDK resmi `anthropic`)
        +-- OpenAIVisionProvider      (API OpenAI-compatible)
        +-- LocalVisionProvider       (server lokal OpenAI-compatible: Ollama, vLLM, LM Studio)

Privasi: pesan error dan log TIDAK BOLEH memuat isi KTP, NIK, base64 gambar, atau API key.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

# Field KTP yang diekstrak (nama key mengikuti spesifikasi fitur).
KTP_FIELDS = (
    "nik", "nama", "tempat_lahir", "tanggal_lahir", "jenis_kelamin",
    "alamat", "rt_rw", "kelurahan", "kecamatan", "agama",
    "status_perkawinan", "pekerjaan", "kewarganegaraan",
)


class VisionError(RuntimeError):
    """Error provider VLM. `message` aman ditampilkan ke user (tanpa data sensitif)."""
    code = "VLM_ERROR"
    http_status = 502
    message = "Foto KTP belum berhasil dibaca. Coba lagi atau isi data secara manual."

    def __init__(self, message: Optional[str] = None):
        self.message = message or self.message
        super().__init__(self.message)


class VisionNotConfigured(VisionError):
    code = "VLM_NOT_CONFIGURED"
    http_status = 503
    message = "Fitur pindai KTP belum aktif. Silakan isi data secara manual."


class VisionTimeout(VisionError):
    code = "VLM_TIMEOUT"
    http_status = 504
    message = "Pembacaan KTP terlalu lama. Coba lagi atau isi data secara manual."


class VisionRateLimited(VisionError):
    code = "VLM_RATE_LIMITED"
    http_status = 429
    message = "Layanan sedang ramai. Coba lagi sebentar lagi ya."


class VisionUnavailable(VisionError):
    code = "VLM_UNAVAILABLE"
    http_status = 503
    message = "Pindai KTP sedang tidak tersedia. Silakan isi data secara manual."


class VisionModelUnavailable(VisionUnavailable):
    code = "VLM_MODEL_UNAVAILABLE"
    message = "Pindai KTP sedang tidak tersedia. Silakan isi data secara manual."


class VisionBadResponse(VisionError):
    code = "VLM_BAD_RESPONSE"
    http_status = 502
    message = "Hasil pembacaan belum bisa dipakai. Coba pindai ulang atau isi manual."


@dataclass
class FieldReading:
    value: Optional[str] = None
    confidence: Optional[float] = None  # 0.0 - 1.0; None = model tidak memberi nilai


@dataclass
class ExtractionResult:
    """Hasil mentah dari VLM setelah di-parse (BELUM divalidasi backend)."""
    document_type: Optional[str] = None
    confidence: Optional[float] = None
    fields: dict = field(default_factory=dict)  # nama field -> FieldReading
    warnings: list = field(default_factory=list)
    provider: str = ""
    model: str = ""


class VisionProvider(ABC):
    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """True bila env cukup untuk memanggil provider (tanpa membocorkan key)."""

    @abstractmethod
    def model_name(self) -> str:
        ...

    @abstractmethod
    def _complete(self, image_bytes: bytes, media_type: str) -> str:
        """Kirim gambar + prompt, kembalikan teks jawaban model. Raise VisionError bila gagal."""

    def extract_ktp(self, image_bytes: bytes, media_type: str) -> ExtractionResult:
        from app.services.vision.parsing import parse_model_output

        if not self.is_configured():
            raise VisionNotConfigured()
        text = self._complete(image_bytes, media_type)
        result = parse_model_output(text)
        result.provider = self.name
        result.model = self.model_name()
        return result
