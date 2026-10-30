"""Claude Vision lewat SDK resmi `anthropic` (Messages API)."""
from __future__ import annotations

import base64
import logging
from typing import Any, Callable, Optional

from app.core.config import settings
from app.services.vision.base import (
    VisionBadResponse, VisionError, VisionModelUnavailable, VisionNotConfigured,
    VisionProvider, VisionRateLimited, VisionTimeout, VisionUnavailable,
)
from app.services.vision.prompt import SYSTEM_PROMPT, USER_PROMPT

logger = logging.getLogger("app.vlm")

DEFAULT_MODEL = "claude-sonnet-5-5"


class AnthropicVisionProvider(VisionProvider):
    name = "anthropic"

    def __init__(self, client_factory: Optional[Callable[[], Any]] = None):
        # client_factory dipakai test untuk menyuntikkan client palsu (tanpa API berbayar).
        self._client_factory = client_factory

    def is_configured(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY) or self._client_factory is not None

    def model_name(self) -> str:
        return settings.VLM_MODEL or DEFAULT_MODEL

    def _client(self):
        if self._client_factory is not None:
            return self._client_factory()
        try:
            import anthropic
        except ImportError as e:
            raise VisionNotConfigured("Paket 'anthropic' belum terpasang di server.") from e
        # max_retries=1: SDK mengulang sekali untuk error sementara; sisanya ditangani caller.
        return anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY, timeout=float(settings.VLM_TIMEOUT_S), max_retries=1,
        )

    def _complete(self, image_bytes: bytes, media_type: str) -> str:
        try:
            import anthropic
        except ImportError as e:
            raise VisionNotConfigured("Paket 'anthropic' belum terpasang di server.") from e

        client = self._client()
        try:
            msg = client.messages.create(
                model=self.model_name(),
                max_tokens=int(settings.VLM_MAX_TOKENS),
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {
                            "type": "base64", "media_type": media_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        }},
                        {"type": "text", "text": USER_PROMPT},
                    ],
                }],
            )
        except VisionError:
            raise
        except Exception as e:  # dipetakan ke error domain; HANYA nama tipe yang di-log
            raise self._map_error(e, anthropic) from None

        if getattr(msg, "stop_reason", None) == "refusal":
            logger.warning("VLM anthropic menolak memproses gambar")
            raise VisionBadResponse()
        parts = [getattr(b, "text", "") for b in (getattr(msg, "content", None) or [])
                 if getattr(b, "type", None) == "text"]
        text = "".join(parts).strip()
        if not text:
            raise VisionBadResponse()
        return text

    @staticmethod
    def _map_error(e: Exception, sdk) -> VisionError:
        logger.warning("VLM anthropic gagal: %s", type(e).__name__)
        # APITimeoutError adalah subclass APIConnectionError -> periksa lebih dulu.
        if isinstance(e, sdk.APITimeoutError):
            return VisionTimeout()
        if isinstance(e, sdk.RateLimitError):
            return VisionRateLimited()
        if isinstance(e, (sdk.AuthenticationError, sdk.PermissionDeniedError)):
            return VisionNotConfigured("Layanan pembaca KTP sedang tidak bisa dipakai. Hubungi admin, atau isi datanya secara manual dulu.")
        if isinstance(e, sdk.NotFoundError):
            return VisionModelUnavailable()
        if isinstance(e, sdk.APIConnectionError):
            return VisionUnavailable()
        if isinstance(e, sdk.APIStatusError):
            status = getattr(e, "status_code", 0) or 0
            if status == 429:
                return VisionRateLimited()
            if status >= 500 or status == 529:
                return VisionUnavailable()
            return VisionBadResponse()
        return VisionUnavailable()
