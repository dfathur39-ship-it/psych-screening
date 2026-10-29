"""Pemilihan provider VLM lewat environment variable (VLM_PROVIDER)."""
from __future__ import annotations

from app.core.config import settings
from app.services.vision.anthropic_provider import AnthropicVisionProvider
from app.services.vision.base import VisionNotConfigured, VisionProvider
from app.services.vision.openai_provider import LocalVisionProvider, OpenAIVisionProvider

PROVIDERS = {
    "anthropic": AnthropicVisionProvider,
    "openai": OpenAIVisionProvider,
    "local": LocalVisionProvider,
}


def resolve_provider_name() -> str:
    """
    VLM_PROVIDER eksplisit selalu menang. Bila kosong (konfigurasi lama):
      - VLM_BASE_URL terisi          -> openai (OpenAI-compatible, perilaku lama)
      - hanya ANTHROPIC_API_KEY ada  -> anthropic
      - lainnya                      -> openai (akan dilaporkan 'belum dikonfigurasi')
    """
    name = (settings.VLM_PROVIDER or "").strip().lower()
    if name:
        return name
    if settings.VLM_BASE_URL:
        return "openai"
    if settings.ANTHROPIC_API_KEY:
        return "anthropic"
    return "openai"


def get_provider() -> VisionProvider:
    name = resolve_provider_name()
    cls = PROVIDERS.get(name)
    if cls is None:
        raise VisionNotConfigured(f"VLM_PROVIDER '{name}' tidak dikenal. Gunakan: {', '.join(PROVIDERS)}.")
    return cls()


def is_vlm_configured() -> bool:
    try:
        return get_provider().is_configured()
    except VisionNotConfigured:
        return False
