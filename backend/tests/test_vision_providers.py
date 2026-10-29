"""Provider VLM: parsing jawaban, Anthropic (client palsu), OpenAI-compatible (httpx palsu), factory."""
import json

import httpx
import pytest

from app.core.config import settings
from app.services.vision import (
    VisionBadResponse, VisionModelUnavailable, VisionNotConfigured, VisionRateLimited,
    VisionTimeout, VisionUnavailable, get_provider, resolve_provider_name,
)
from app.services.vision.anthropic_provider import AnthropicVisionProvider
from app.services.vision.openai_provider import LocalVisionProvider, OpenAIVisionProvider
from app.services.vision.parsing import parse_model_output
from tests.ktp_fixtures import VALID_NIK, vlm_json

IMG = b"\xff\xd8\xff fake-bytes"


# ---------- parsing ----------
def test_parse_valid_json():
    r = parse_model_output(vlm_json())
    assert r.document_type == "KTP" and r.fields["nik"].value == VALID_NIK
    assert r.fields["nik"].confidence == 0.97


def test_parse_tolerates_markdown_fence_and_preamble():
    assert parse_model_output("```json\n" + vlm_json() + "\n```").fields["nama"].value == "BUDI SANTOSO"
    assert parse_model_output("Berikut hasilnya:\n" + vlm_json()).fields["nama"].value == "BUDI SANTOSO"


@pytest.mark.parametrize("bad", ["", "maaf, saya tidak bisa membaca gambar ini", "[1, 2, 3]", '{"fields": ', "null"])
def test_parse_malformed_raises(bad):
    with pytest.raises(VisionBadResponse):
        parse_model_output(bad)


def test_parse_flat_legacy_schema_and_percent_confidence():
    r = parse_model_output(json.dumps({"nik": VALID_NIK, "nama": "BUDI", "pekerjaan_ktp": "PNS", "confidence": 90}))
    assert r.fields["pekerjaan"].value == "PNS" and r.confidence == 0.9


def test_parse_null_like_values_become_none():
    r = parse_model_output('{"fields": {"nama": {"value": "null", "confidence": 0.2}, "alamat": {"value": "-", "confidence": "x"}}}')
    assert r.fields["nama"].value is None and r.fields["alamat"].value is None
    assert r.fields["alamat"].confidence is None


# ---------- Anthropic ----------
class _Block:
    def __init__(self, text, type="text"):
        self.type, self.text = type, text


class _Msg:
    def __init__(self, text, stop_reason="end_turn"):
        self.content, self.stop_reason = [_Block(text)], stop_reason


class _FakeAnthropic:
    def __init__(self, reply=None, exc=None):
        self.reply, self.exc, self.calls = reply, exc, []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        if self.exc:
            raise self.exc
        return self.reply


def _anthropic(reply=None, exc=None, monkeypatch=None):
    fake = _FakeAnthropic(reply, exc)
    return AnthropicVisionProvider(client_factory=lambda: fake), fake


def test_anthropic_success_builds_correct_request():
    p, fake = _anthropic(_Msg(vlm_json()))
    r = p.extract_ktp(IMG, "image/jpeg")
    assert r.provider == "anthropic" and r.fields["nama"].value == "BUDI SANTOSO"
    call = fake.calls[0]
    assert call["model"] == p.model_name() and call["max_tokens"] == settings.VLM_MAX_TOKENS
    assert "JSON" in call["system"]
    img = call["messages"][0]["content"][0]
    assert img["type"] == "image" and img["source"]["type"] == "base64" and img["source"]["media_type"] == "image/jpeg"


def test_anthropic_model_comes_from_env(monkeypatch):
    monkeypatch.setattr(settings, "VLM_MODEL", "claude-test-model", raising=False)
    p, fake = _anthropic(_Msg(vlm_json()))
    p.extract_ktp(IMG, "image/jpeg")
    assert fake.calls[0]["model"] == "claude-test-model"


def test_anthropic_not_configured_without_key(monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "", raising=False)
    with pytest.raises(VisionNotConfigured):
        AnthropicVisionProvider().extract_ktp(IMG, "image/jpeg")


def test_anthropic_malformed_and_empty_response():
    p, _ = _anthropic(_Msg("bukan json sama sekali"))
    with pytest.raises(VisionBadResponse):
        p.extract_ktp(IMG, "image/jpeg")
    p, _ = _anthropic(_Msg(""))
    with pytest.raises(VisionBadResponse):
        p.extract_ktp(IMG, "image/jpeg")


def test_anthropic_refusal_is_bad_response():
    p, _ = _anthropic(_Msg(vlm_json(), stop_reason="refusal"))
    with pytest.raises(VisionBadResponse):
        p.extract_ktp(IMG, "image/jpeg")


def _sdk_errors():
    import anthropic
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    def status_err(cls, code):
        return cls("x", response=httpx.Response(code, request=req), body=None)
    return [
        (anthropic.APITimeoutError(request=req), VisionTimeout),
        (anthropic.APIConnectionError(request=req), VisionUnavailable),
        (status_err(anthropic.RateLimitError, 429), VisionRateLimited),
        (status_err(anthropic.AuthenticationError, 401), VisionNotConfigured),
        (status_err(anthropic.NotFoundError, 404), VisionModelUnavailable),
        (status_err(anthropic.InternalServerError, 500), VisionUnavailable),
        (status_err(anthropic.BadRequestError, 400), VisionBadResponse),
        (RuntimeError("tak terduga"), VisionUnavailable),
    ]


def test_anthropic_sdk_errors_are_mapped():
    for exc, expected in _sdk_errors():
        p, _ = _anthropic(exc=exc)
        with pytest.raises(expected):
            p.extract_ktp(IMG, "image/jpeg")


def test_anthropic_error_message_never_leaks_details():
    import anthropic
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    exc = anthropic.AuthenticationError("invalid x-api-key sk-ant-SECRET", response=httpx.Response(401, request=req), body=None)
    p, _ = _anthropic(exc=exc)
    with pytest.raises(VisionNotConfigured) as e:
        p.extract_ktp(IMG, "image/jpeg")
    assert "SECRET" not in e.value.message and "sk-ant" not in str(e.value)


# ---------- OpenAI-compatible / local ----------
class _Resp:
    def __init__(self, body=None, status=200):
        self._body, self.status_code = body, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=httpx.Request("POST", "http://x"),
                                        response=httpx.Response(self.status_code))

    def json(self):
        return self._body


def _openai_settings(monkeypatch):
    monkeypatch.setattr(settings, "VLM_BASE_URL", "https://fake.local/v1", raising=False)
    monkeypatch.setattr(settings, "VLM_API_KEY", "k", raising=False)
    monkeypatch.setattr(settings, "VLM_MODEL", "m", raising=False)


def test_openai_success(monkeypatch):
    _openai_settings(monkeypatch)
    seen = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        seen.update(url=url, payload=json, headers=headers)
        return _Resp({"choices": [{"message": {"content": vlm_json()}}]})
    monkeypatch.setattr(httpx, "post", fake_post)
    r = OpenAIVisionProvider().extract_ktp(IMG, "image/png")
    assert r.provider == "openai" and r.fields["nik"].value == VALID_NIK
    assert seen["url"] == "https://fake.local/v1/chat/completions"
    assert seen["payload"]["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")


@pytest.mark.parametrize("status,expected", [
    (429, VisionRateLimited), (401, VisionNotConfigured), (404, VisionModelUnavailable),
    (503, VisionUnavailable), (400, VisionBadResponse),
])
def test_openai_http_errors_mapped(monkeypatch, status, expected):
    _openai_settings(monkeypatch)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp({}, status))
    with pytest.raises(expected):
        OpenAIVisionProvider().extract_ktp(IMG, "image/jpeg")


def test_openai_timeout_and_network(monkeypatch):
    _openai_settings(monkeypatch)

    def timeout(*a, **k):
        raise httpx.ReadTimeout("t")

    def net(*a, **k):
        raise httpx.ConnectError("c")
    monkeypatch.setattr(httpx, "post", timeout)
    with pytest.raises(VisionTimeout):
        OpenAIVisionProvider().extract_ktp(IMG, "image/jpeg")
    monkeypatch.setattr(httpx, "post", net)
    with pytest.raises(VisionUnavailable):
        OpenAIVisionProvider().extract_ktp(IMG, "image/jpeg")


def test_openai_non_openai_schema_and_non_json(monkeypatch):
    _openai_settings(monkeypatch)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp({"unexpected": 1}))
    with pytest.raises(VisionBadResponse):
        OpenAIVisionProvider().extract_ktp(IMG, "image/jpeg")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp({"choices": [{"message": {"content": "halo"}}]}))
    with pytest.raises(VisionBadResponse):
        OpenAIVisionProvider().extract_ktp(IMG, "image/jpeg")


def test_local_provider_defaults(monkeypatch):
    monkeypatch.setattr(settings, "VLM_BASE_URL", "", raising=False)
    monkeypatch.setattr(settings, "VLM_API_KEY", "", raising=False)
    monkeypatch.setattr(settings, "VLM_MODEL", "llava", raising=False)
    p = LocalVisionProvider()
    assert p.is_configured() and p._base_url() == "http://localhost:11434/v1"


# ---------- factory ----------
def test_factory_explicit_provider_wins(monkeypatch):
    monkeypatch.setattr(settings, "VLM_BASE_URL", "https://x/v1", raising=False)
    for name, cls in (("anthropic", AnthropicVisionProvider), ("openai", OpenAIVisionProvider), ("local", LocalVisionProvider)):
        monkeypatch.setattr(settings, "VLM_PROVIDER", name, raising=False)
        assert isinstance(get_provider(), cls)


def test_factory_infers_legacy_and_anthropic(monkeypatch):
    monkeypatch.setattr(settings, "VLM_PROVIDER", "", raising=False)
    monkeypatch.setattr(settings, "VLM_BASE_URL", "https://x/v1", raising=False)
    assert resolve_provider_name() == "openai"
    monkeypatch.setattr(settings, "VLM_BASE_URL", "", raising=False)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "sk-test", raising=False)
    assert resolve_provider_name() == "anthropic"


def test_factory_unknown_provider(monkeypatch):
    monkeypatch.setattr(settings, "VLM_PROVIDER", "skynet", raising=False)
    with pytest.raises(VisionNotConfigured):
        get_provider()
