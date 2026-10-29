import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/psych_screening"
    SECRET_KEY: str = "CHANGE_ME_DEV_ONLY"
    JWT_SECRET: str = "CHANGE_ME_DEV_ONLY"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:5173"
    OCR_PROVIDER: str = "auto"  # tesseract | vlm | auto (default: VLM dulu, fallback tesseract)
    OCR_API_KEY: str = ""
    # VLM (OpenAI-compatible, mis. OpenAI / Together / Groq / Ollama OpenAI-mode)
    VLM_BASE_URL: str = ""
    VLM_API_KEY: str = ""
    VLM_MODEL: str = ""
    VLM_TIMEOUT_S: int = 30
    # Pilih provider VLM: anthropic | openai | local. Kosong = otomatis (kompatibel dengan
    # konfigurasi lama: bila VLM_BASE_URL terisi -> openai-compatible, bila hanya
    # ANTHROPIC_API_KEY terisi -> anthropic).
    VLM_PROVIDER: str = ""
    ANTHROPIC_API_KEY: str = ""
    VLM_MAX_TOKENS: int = 2048
    # Ambang confidence per field (0.0-1.0). Di bawah ini -> field ditandai "perlu diperiksa".
    VLM_CONFIDENCE_THRESHOLD: float = 0.80
    # Auto-confirm (alur lama /api/ocr/ktp): menyimpan hasil AI TANPA dicek user.
    # Default dimatikan: hasil AI harus selalu diperiksa user sebelum disimpan.
    VLM_AUTO_CONFIRM: bool = False
    VLM_AUTO_CONFIRM_MIN_CONFIDENCE: int = 80
    TESSERACT_CMD: str = ""
    UPLOAD_DIR: str = "/data/uploads/ktp"
    KTP_RETENTION_DELETE_AFTER_OCR: bool = True
    MAX_UPLOAD_SIZE_MB: int = 5
    # --- Scan KTP (POST /api/ktp/scan) ---
    MAX_KTP_FILE_SIZE_MB: float = 5  # API Anthropic menolak gambar > 5 MB; naikkan hanya bila perlu
    KTP_MIN_IMAGE_SIDE_PX: int = 200   # sisi terpendek minimal
    KTP_MAX_IMAGE_SIDE_PX: int = 12000  # sisi terpanjang maksimal (anti decompression bomb)
    KTP_VLM_IMAGE_MAX_SIDE_PX: int = 1600  # gambar diperkecil ke ukuran ini sebelum dikirim ke VLM
    KTP_PREPROCESS: bool = True
    KTP_SCAN_RATE_LIMIT: str = "10/minute"  # per IP (slowapi)
    KTP_SCAN_MAX_PER_PARTICIPANT: int = 8   # maksimal pemanggilan VLM per peserta per jendela waktu
    KTP_SCAN_WINDOW_S: int = 3600
    KTP_SCAN_GLOBAL_MAX_PER_WINDOW: int = 500  # pagar biaya: total pemanggilan VLM semua peserta
    ENV: str = "development"

    @property
    def cors_origins_list(self):
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
