"""Provider OpenAI-compatible (OpenAI, Together, Groq, ...) dan server lokal (Ollama, vLLM)."""
from __future__ import annotations

import base64
import logging

from app.core.config import settings
from app.services.vision.base import (
    VisionBadResponse, VisionError, VisionModelUnavailable, VisionNotConfigured,
    VisionProvider, VisionRateLimited, VisionTimeout, VisionUnavailable,
)
from app.services.vision.prompt import SYSTEM_PROMPT, USER_PROMPT

logger = logging.getLogger("app.vlm")


class OpenAIVisionProvider(VisionProvider):
    name = "openai"

    def _base_url(self) -> str:
        return settings.VLM_BASE_URL

    def _api_key(self) -> str:
        return settings.VLM_API_KEY

    def is_configured(self) -> bool:
        return bool(self._api_key() and self._base_url() and settings.VLM_MODEL)

    def model_name(self) -> str:
        return settings.VLM_MODEL

    def _complete(self, image_bytes: bytes, media_type: str) -> str:
        try:
            import httpx
        except ImportError as e:
            raise VisionNotConfigured("httpx tidak terpasang untuk VLM.") from e

        data_url = f"data:{media_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        payload = {
            "model": self.model_name(),
            "temperature": 0,
            "max_tokens": int(settings.VLM_MAX_TOKENS),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]},
            ],
        }
        headers = {"Authorization": f"Bearer {self._api_key()}", "Content-Type": "application/json"}
        url = self._base_url().rstrip("/") + "/chat/completions"

        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=settings.VLM_TIMEOUT_S)
            resp.raise_for_status()
            body = resp.json()
        except httpx.TimeoutException:
            logger.warning("VLM %s timeout", self.name)
            raise VisionTimeout() from None
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            logger.warning("VLM %s HTTP %s", self.name, status)
            if status == 429:
                raise VisionRateLimited() from None
            if status in (401, 403):
                raise VisionNotConfigured("Layanan pembaca KTP sedang tidak bisa dipakai. Hubungi admin, atau isi datanya secara manual dulu.") from None
            if status == 404:
                raise VisionModelUnavailable() from None
            if status >= 500:
                raise VisionUnavailable() from None
            raise VisionBadResponse() from None
        except httpx.RequestError as e:
            logger.warning("VLM %s network error: %s", self.name, type(e).__name__)
            raise VisionUnavailable() from None
        except VisionError:
            raise
        except Exception as e:
            logger.warning("VLM %s gagal: %s", self.name, type(e).__name__)
            raise VisionBadResponse() from None

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            logger.warning("VLM %s: respons tidak sesuai skema OpenAI", self.name)
            raise VisionBadResponse() from None
        if isinstance(content, list):  # beberapa server mengembalikan list of parts
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        if not isinstance(content, str) or not content.strip():
            raise VisionBadResponse()
        return content


class LocalVisionProvider(OpenAIVisionProvider):
    """Server VLM lokal yang OpenAI-compatible. Key tidak wajib; base URL default Ollama."""
    name = "local"

    def _base_url(self) -> str:
        return settings.VLM_BASE_URL or "http://localhost:11434/v1"

    def _api_key(self) -> str:
        return settings.VLM_API_KEY or "local"

    def is_configured(self) -> bool:
        return bool(settings.VLM_MODEL)
