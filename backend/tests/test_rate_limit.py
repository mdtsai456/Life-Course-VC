"""Tests for slowapi rate limiting on /api/clone-voice."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    _APP_MODULES,
    _cleanup_modules,
    _make_mock_tts_api,
    _make_standard_patches,
)


WEBM_HEADER = b"\x1a\x45\xdf\xa3" + b"\x00" * 4
WAV_STUB = b"RIFF\x00\x00\x00\x00WAVEfmt "


def _synth_side_effect(text, speaker_wav, language, file_path):
    with open(file_path, "wb") as f:
        f.write(WAV_STUB)


@pytest.fixture()
def rate_limited_client(request):
    """Client with rate limit enabled and a small limit for fast testing."""
    params = getattr(request, "param", {})
    clone_limit = params.get("clone_limit", "3/minute")
    health_limit = params.get("health_limit")
    prior_enabled = os.environ.get("RATE_LIMIT_ENABLED")
    prior_limit = os.environ.get("RATE_LIMIT_CLONE")
    prior_health_limit = os.environ.get("RATE_LIMIT_HEALTH")
    os.environ["RATE_LIMIT_ENABLED"] = "true"
    os.environ["RATE_LIMIT_CLONE"] = clone_limit
    if health_limit is not None:
        os.environ["RATE_LIMIT_HEALTH"] = health_limit

    mock_torch = MagicMock(name="torch")
    mock_torch.cuda.is_available.return_value = False
    mock_tts_api, _ = _make_mock_tts_api()
    patches = _make_standard_patches(mock_torch, mock_tts_api)

    saved = {m: sys.modules[m] for m in _APP_MODULES if m in sys.modules}

    with patch.dict(sys.modules, patches):
        _cleanup_modules()
        from app.main import app
        with TestClient(app) as c:
            yield c
        _cleanup_modules()

    for mod, orig in saved.items():
        sys.modules[mod] = orig
        parts = mod.rsplit(".", 1)
        if len(parts) == 2 and parts[0] in sys.modules:
            setattr(sys.modules[parts[0]], parts[1], orig)

    if prior_enabled is None:
        os.environ["RATE_LIMIT_ENABLED"] = "false"
    else:
        os.environ["RATE_LIMIT_ENABLED"] = prior_enabled
    if prior_limit is None:
        os.environ.pop("RATE_LIMIT_CLONE", None)
    else:
        os.environ["RATE_LIMIT_CLONE"] = prior_limit
    if health_limit is not None:
        if prior_health_limit is None:
            os.environ.pop("RATE_LIMIT_HEALTH", None)
        else:
            os.environ["RATE_LIMIT_HEALTH"] = prior_health_limit


def _valid_audio_payload() -> bytes:
    return WEBM_HEADER + b"\x00" * 1016


def _post_clone(client):
    return client.post(
        "/api/clone-voice",
        files={"file": ("rec.webm", _valid_audio_payload(), "audio/webm")},
        data={"text": "hello world"},
    )


class TestCloneRateLimit:
    def test_exceeds_limit_returns_429(self, rate_limited_client, voice_mocks):
        rate_limited_client.app.state.tts_model.tts_to_file.side_effect = _synth_side_effect
        voice_mocks.setup()

        # Limit is 3/minute. 3 should pass, 4th should be 429.
        for _ in range(3):
            resp = _post_clone(rate_limited_client)
            assert resp.status_code == 200, resp.text

        resp = _post_clone(rate_limited_client)
        assert resp.status_code == 429
        assert "detail" in resp.json()
        assert resp.headers.get("Retry-After") == "60"

    def test_limit_headers_present_on_success(self, rate_limited_client, voice_mocks):
        rate_limited_client.app.state.tts_model.tts_to_file.side_effect = _synth_side_effect
        voice_mocks.setup()

        resp = _post_clone(rate_limited_client)
        assert resp.status_code == 200
        # slowapi headers_enabled=True
        assert "x-ratelimit-limit" in {h.lower() for h in resp.headers.keys()}

    @pytest.mark.parametrize(
        "rate_limited_client",
        [{"clone_limit": "1/hour"}],
        indirect=True,
    )
    def test_retry_after_matches_clone_window(self, rate_limited_client, voice_mocks):
        rate_limited_client.app.state.tts_model.tts_to_file.side_effect = _synth_side_effect
        voice_mocks.setup()

        assert _post_clone(rate_limited_client).status_code == 200
        resp = _post_clone(rate_limited_client)
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "3600"

    @pytest.mark.parametrize(
        "rate_limited_client",
        [{"clone_limit": "100/minute;1/day"}],
        indirect=True,
    )
    def test_retry_after_uses_triggered_limit_when_multiple_limits_exist(self, rate_limited_client, voice_mocks):
        rate_limited_client.app.state.tts_model.tts_to_file.side_effect = _synth_side_effect
        voice_mocks.setup()

        assert _post_clone(rate_limited_client).status_code == 200
        resp = _post_clone(rate_limited_client)
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "86400"


class TestHealthNotRateLimitedAggressively:
    def test_health_endpoint_accessible(self, rate_limited_client):
        # Health limit is 60/minute by default — a handful of requests should pass.
        for _ in range(5):
            resp = rate_limited_client.get("/health")
            assert resp.status_code == 200

    @pytest.mark.parametrize(
        "rate_limited_client",
        [{"health_limit": "1/hour"}],
        indirect=True,
    )
    def test_health_retry_after_matches_health_window(self, rate_limited_client):
        assert rate_limited_client.get("/health").status_code == 200
        resp = rate_limited_client.get("/health")
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "3600"
