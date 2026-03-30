"""Shared fixtures for backend tests.

Uses sys.modules patching instead of simple @patch because torch and
TTS are imported at module level in main.py.  We need to inject the mocks
*before* the module is imported, not after.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


_APP_MODULES = [
    "app.main",
    "app.config",
    "app.routes.voice",
]


def _cleanup_modules():
    """Remove cached app modules so the next import gets a fresh copy."""
    for mod in _APP_MODULES:
        sys.modules.pop(mod, None)


def _make_mock_tts_api():
    """Return (mock_tts_api, mock_tts_instance) for sys.modules patching."""
    mock_tts_instance = MagicMock(name="tts_instance")
    mock_tts_instance.to.return_value = mock_tts_instance
    mock_tts_cls = MagicMock(name="TTS_class", return_value=mock_tts_instance)
    mock_tts_api = MagicMock(name="TTS.api")
    mock_tts_api.TTS = mock_tts_cls
    return mock_tts_api, mock_tts_instance


def _make_standard_patches(mock_torch, mock_tts_api):
    """Return the standard sys.modules patches dict for torch and TTS."""
    return {
        "torch": mock_torch,
        "TTS": MagicMock(name="TTS_module", api=mock_tts_api),
        "TTS.api": mock_tts_api,
    }


@pytest.fixture()
def client():
    """Yield a TestClient with torch and TTS mocked out."""
    mock_torch = MagicMock(name="torch")
    mock_torch.cuda.is_available.return_value = False

    mock_tts_api, _ = _make_mock_tts_api()

    patches = _make_standard_patches(mock_torch, mock_tts_api)

    # Save original modules so top-level imports in other test files
    # keep referencing the correct module globals after cleanup.
    saved = {m: sys.modules[m] for m in _APP_MODULES if m in sys.modules}

    with patch.dict(sys.modules, patches):
        _cleanup_modules()

        from app.main import app

        with TestClient(app) as c:
            yield c

        _cleanup_modules()

    # Restore original modules in sys.modules AND as package attributes,
    # so that unittest.mock.patch() resolves to the same module objects
    # that top-level imports in other test files reference.
    for mod, orig in saved.items():
        sys.modules[mod] = orig
        parts = mod.rsplit(".", 1)
        if len(parts) == 2 and parts[0] in sys.modules:
            setattr(sys.modules[parts[0]], parts[1], orig)


@pytest.fixture()
def voice_mocks():
    """Patch _estimate_pcm_size and AudioSegment for voice endpoint tests.

    Yields a namespace with:
        .audio_seg_cls  - the mocked AudioSegment class
        .setup(duration_ms=5000) - configures the standard mock and returns mock_seg
    """
    from types import SimpleNamespace

    with patch("app.routes.voice._estimate_pcm_size", return_value=None), \
         patch("app.routes.voice.AudioSegment") as mock_cls:

        def setup(duration_ms: int = 5000):
            mock_seg = MagicMock()
            mock_seg.raw_data = b"\x00" * 100
            mock_seg.__len__ = MagicMock(return_value=duration_ms)
            mock_cls.from_file.return_value = mock_seg

            def _export_side_effect(buf, **_kwargs):
                buf.write(b"RIFF\x00\x00\x00\x00WAVEfmt ")
            mock_seg.export.side_effect = _export_side_effect
            return mock_seg

        yield SimpleNamespace(audio_seg_cls=mock_cls, setup=setup)


@pytest.fixture()
def mock_ffprobe():
    """Patch subprocess.run for ffprobe-based tests in voice module."""
    with patch("app.routes.voice.subprocess.run") as mock_run:
        yield mock_run
