"""Tests for the /api/clone-voice endpoint and _detect_audio_type helper."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydub.exceptions import CouldntDecodeError

from tests.conftest import _cleanup_modules, _make_standard_patches

from app.constants import MAX_FILE_SIZE, MAX_PCM_SIZE
from app.routes.voice import (
    AudioConversionError,
    NoOutputError,
    VoiceInferenceError,
    _convert_to_wav,
    _detect_audio_type,
    _detect_language,
    _estimate_pcm_size,
    _run_xtts,
)

# ---------------------------------------------------------------------------
# Magic bytes helpers
# ---------------------------------------------------------------------------
WEBM_HEADER = b"\x1a\x45\xdf\xa3" + b"\x00" * 4  # EBML magic + padding to 8 bytes
OGG_HEADER = b"OggS" + b"\x00" * 4
# MP4: 4 bytes size + "ftyp" at offset 4
MP4_HEADER = b"\x00\x00\x00\x18" + b"ftyp" + b"isom" + b"\x00" * 4

WAV_STUB = b"RIFF\x00\x00\x00\x00WAVEfmt "


def _make_audio(header: bytes, size: int = 1024) -> bytes:
    """Return header padded to *size* bytes."""
    return header + b"\x00" * (size - len(header))


def _make_synth_side_effect(wav_bytes: bytes):
    """Return a tts_to_file side_effect that writes wav_bytes to file_path."""
    def _side_effect(text, speaker_wav, language, file_path):
        with open(file_path, "wb") as f:
            f.write(wav_bytes)
    return _side_effect



# ===========================================================================
# _detect_audio_type unit tests
# ===========================================================================
class TestDetectAudioType:
    def test_webm(self):
        assert _detect_audio_type(_make_audio(WEBM_HEADER)) == "audio/webm"

    def test_ogg(self):
        assert _detect_audio_type(_make_audio(OGG_HEADER)) == "audio/ogg"

    def test_mp4_ftyp_at_offset_4(self):
        assert _detect_audio_type(_make_audio(MP4_HEADER)) == "audio/mp4"

    def test_mp4_ftyp_must_be_at_offset_4_not_0(self):
        """ftyp at offset 0 should NOT be detected as MP4."""
        bad = b"ftyp" + b"\x00" * 4
        assert _detect_audio_type(bad) is None

    def test_too_short_returns_none(self):
        assert _detect_audio_type(b"\x1a\x45\xdf") is None  # 3 bytes
        assert _detect_audio_type(b"") is None
        assert _detect_audio_type(b"\x00" * 7) is None

    def test_exactly_8_bytes(self):
        assert _detect_audio_type(WEBM_HEADER) == "audio/webm"

    def test_unknown_magic_returns_none(self):
        assert _detect_audio_type(b"\x00" * 16) is None
        assert _detect_audio_type(b"RIFF\x00\x00\x00\x00") is None


# ===========================================================================
# _estimate_pcm_size unit tests
# ===========================================================================
def _ffprobe_json(streams, fmt=None):
    """Build a fake ffprobe JSON stdout for subprocess mock."""
    import json as _json

    payload = {"streams": streams, "format": fmt or {}}
    return MagicMock(stdout=_json.dumps(payload).encode())


class TestEstimatePcmSize:
    def test_returns_estimated_size(self, mock_ffprobe):
        mock_ffprobe.return_value = _ffprobe_json([
            {"codec_type": "audio", "duration": "10.0",
             "sample_rate": "48000", "channels": 2},
        ])
        assert _estimate_pcm_size(b"data", "webm") == 10 * 48000 * 2 * 2

    def test_uses_format_duration_fallback(self, mock_ffprobe):
        mock_ffprobe.return_value = _ffprobe_json(
            [{"codec_type": "audio", "sample_rate": "44100", "channels": 1}],
            fmt={"duration": "5.0"},
        )
        assert _estimate_pcm_size(b"data", "ogg") == int(5.0 * 44100 * 1 * 2)

    def test_returns_none_on_no_audio_stream(self, mock_ffprobe):
        mock_ffprobe.return_value = _ffprobe_json([{"codec_type": "video"}])
        assert _estimate_pcm_size(b"data", "webm") is None

    def test_returns_none_on_invalid_json(self, mock_ffprobe):
        mock_ffprobe.return_value = MagicMock(stdout=b"not json")
        assert _estimate_pcm_size(b"data", "webm") is None

    def test_returns_none_on_missing_metadata(self, mock_ffprobe):
        mock_ffprobe.return_value = _ffprobe_json([
            {"codec_type": "audio", "duration": "10.0", "channels": 2},
        ])
        assert _estimate_pcm_size(b"data", "webm") is None

    def test_ffprobe_not_found_raises(self, mock_ffprobe):
        mock_ffprobe.side_effect = FileNotFoundError("ffprobe")
        with pytest.raises(FileNotFoundError):
            _estimate_pcm_size(b"data", "webm")

    def test_timeout_returns_none(self, mock_ffprobe):
        mock_ffprobe.side_effect = subprocess.TimeoutExpired(cmd="ffprobe", timeout=10)
        assert _estimate_pcm_size(b"data", "webm") is None


# ===========================================================================
# _convert_to_wav unit tests
# ===========================================================================
class TestConvertToWav:
    @patch("app.routes.voice._estimate_pcm_size", return_value=None)
    def test_success(self, _mock_estimate):
        with patch("app.routes.voice.AudioSegment") as mock_cls:
            mock_audio = MagicMock()
            mock_audio.raw_data = b"\x00" * 100
            mock_audio.__len__ = MagicMock(return_value=5000)  # 5 seconds
            mock_cls.from_file.return_value = mock_audio

            def _export_side_effect(buf, **_kwargs):
                buf.write(WAV_STUB)

            mock_audio.export.side_effect = _export_side_effect

            wav_bytes, duration_secs = _convert_to_wav(b"fake-audio", "webm")
            assert wav_bytes == WAV_STUB
            assert duration_secs == 5.0
            mock_cls.from_file.assert_called_once()

    @patch("app.routes.voice._estimate_pcm_size", return_value=None)
    def test_decode_error(self, _mock_estimate):
        with patch("app.routes.voice.AudioSegment") as mock_cls:
            mock_cls.from_file.side_effect = CouldntDecodeError("bad file")
            with pytest.raises(AudioConversionError, match="無法解碼音訊檔案"):
                _convert_to_wav(b"bad-audio", "webm")

    @patch("app.routes.voice._estimate_pcm_size", return_value=None)
    def test_ffmpeg_not_found(self, _mock_estimate):
        with patch("app.routes.voice.AudioSegment") as mock_cls:
            mock_cls.from_file.side_effect = FileNotFoundError("ffmpeg not found")
            with pytest.raises(FileNotFoundError):
                _convert_to_wav(b"some-audio", "webm")

    @patch("app.routes.voice._estimate_pcm_size", return_value=None)
    def test_oversized_pcm(self, _mock_estimate):
        with patch("app.routes.voice.AudioSegment") as mock_cls:
            mock_audio = MagicMock()
            mock_audio.raw_data = b"\x00" * (MAX_PCM_SIZE + 1)
            mock_cls.from_file.return_value = mock_audio
            with pytest.raises(AudioConversionError, match="音訊解壓後超過大小限制"):
                _convert_to_wav(b"some-audio", "webm")

    def test_precheck_rejects_oversized(self):
        with patch("app.routes.voice._estimate_pcm_size", return_value=MAX_PCM_SIZE + 1), \
             patch("app.routes.voice.AudioSegment") as mock_cls:
            with pytest.raises(AudioConversionError, match="音訊解壓後超過大小限制"):
                _convert_to_wav(b"some-audio", "webm")
            mock_cls.from_file.assert_not_called()

    def test_precheck_ffprobe_missing(self):
        with patch("app.routes.voice._estimate_pcm_size", side_effect=FileNotFoundError("ffprobe")):
            with pytest.raises(FileNotFoundError):
                _convert_to_wav(b"some-audio", "webm")


# ===========================================================================
# /api/clone-voice endpoint tests
# ===========================================================================
class TestCloneVoiceEndpoint:
    # -- success --
    @pytest.mark.parametrize(
        "header, filename, mime",
        [
            (WEBM_HEADER, "rec.webm", "audio/webm"),
            (OGG_HEADER, "rec.ogg", "audio/ogg"),
            (MP4_HEADER, "rec.m4a", "audio/mp4"),
        ],
        ids=["webm", "ogg", "mp4"],
    )
    def test_success(self, client, voice_mocks, header, filename, mime):
        audio = _make_audio(header)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup()
        resp = client.post(
            "/api/clone-voice",
            files={"file": (filename, audio, mime)},
            data={"text": "hello"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/wav"
        assert resp.headers["content-disposition"] == 'attachment; filename="cloned.wav"'
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert resp.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
        assert resp.content == WAV_STUB

    # -- MIME type is informational; magic bytes decide acceptance --
    def test_accept_mismatched_mime_with_valid_magic(self, client, voice_mocks):
        """Mismatched MIME (audio/wav) but valid WebM magic bytes → accepted."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup()
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.wav", audio, "audio/wav")},
            data={"text": "hello"},
        )
        assert resp.status_code == 200

    def test_accept_octet_stream_with_valid_magic(self, client, voice_mocks):
        """application/octet-stream with valid OGG magic bytes → accepted."""
        audio = _make_audio(OGG_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup()
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.ogg", audio, "application/octet-stream")},
            data={"text": "hello"},
        )
        assert resp.status_code == 200

    def test_reject_mime_with_codec_suffix(self, client, voice_mocks):
        """audio/webm;codecs=opus should still be accepted (stripped to audio/webm)."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup()
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm;codecs=opus")},
            data={"text": "hello"},
        )
        assert resp.status_code == 200

    # -- text validation (400) --
    def test_reject_missing_text(self, client):
        audio = _make_audio(WEBM_HEADER)
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
        )
        assert resp.status_code == 400
        assert "文字不得為空" in resp.json()["detail"]

    def test_reject_empty_text(self, client):
        audio = _make_audio(WEBM_HEADER)
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": ""},
        )
        assert resp.status_code == 400

    def test_reject_whitespace_only_text(self, client):
        audio = _make_audio(WEBM_HEADER)
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "   "},
        )
        assert resp.status_code == 400

    # -- file size validation (413) --
    def test_reject_oversized_file(self, client):
        big = _make_audio(WEBM_HEADER, size=MAX_FILE_SIZE + 1)
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", big, "audio/webm")},
            data={"text": "hello"},
        )
        assert resp.status_code == 413
        assert "檔案過大" in resp.json()["detail"]

    def test_accept_file_exactly_10mb(self, client, voice_mocks):
        """File exactly 10 MB → should pass size validation."""
        audio = _make_audio(WEBM_HEADER, size=MAX_FILE_SIZE)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup()
        # Override the estimate to avoid conservative fallback rejecting large files
        with patch("app.routes.voice._estimate_pcm_size", return_value=1024):
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.webm", audio, "audio/webm")},
                data={"text": "hello"},
            )
        assert resp.status_code == 200

    # -- magic bytes validation (415) --
    def test_reject_bad_magic_bytes(self, client):
        """Valid MIME but file content doesn't match any known audio format."""
        fake = b"\x00" * 1024
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", fake, "audio/webm")},
            data={"text": "hello"},
        )
        assert resp.status_code == 415
        assert "有效的音訊格式" in resp.json()["detail"]

    # -- conversion error paths --
    def test_conversion_failure_returns_422(self, client, voice_mocks):
        audio = _make_audio(WEBM_HEADER)
        voice_mocks.audio_seg_cls.from_file.side_effect = CouldntDecodeError("bad")
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "hello"},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"] == "無法解碼音訊檔案。"

    def test_oversized_pcm_returns_422(self, client, voice_mocks):
        audio = _make_audio(WEBM_HEADER)
        mock_seg = MagicMock()
        mock_seg.raw_data = b"\x00" * (MAX_PCM_SIZE + 1)
        voice_mocks.audio_seg_cls.from_file.return_value = mock_seg
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "hello"},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"] == "音訊解壓後超過大小限制。"

    def test_export_failure_returns_422(self, client, voice_mocks):
        audio = _make_audio(WEBM_HEADER)
        mock_seg = MagicMock()
        mock_seg.raw_data = b"\x00" * 100
        voice_mocks.audio_seg_cls.from_file.return_value = mock_seg
        mock_seg.export.side_effect = Exception("encode failed")
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "hello"},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"] == "音訊編碼失敗。"

    def test_ffmpeg_missing_returns_503(self, client):
        audio = _make_audio(WEBM_HEADER)
        with patch("app.routes.voice._convert_to_wav", side_effect=FileNotFoundError("ffmpeg")):
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.webm", audio, "audio/webm")},
                data={"text": "hello"},
            )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "音訊轉換服務暫時無法使用。"


# ===========================================================================
# XTTS v2 model preload tests
# ===========================================================================
class TestXttsPreload:
    def test_tts_model_on_app_state(self, client):
        """After startup, app.state.tts_model should be set."""
        assert hasattr(client.app.state, "tts_model")
        assert client.app.state.tts_model is not None

    def test_xtts_lock_on_app_state(self, client):
        """After startup, app.state.xtts_lock should be an asyncio.Lock."""
        assert hasattr(client.app.state, "xtts_lock")
        assert isinstance(client.app.state.xtts_lock, asyncio.Lock)

    def test_semaphore_on_app_state(self, client):
        """After startup, app.state.xtts_semaphore should be an asyncio.Semaphore."""
        assert hasattr(client.app.state, "xtts_semaphore")
        assert isinstance(client.app.state.xtts_semaphore, asyncio.Semaphore)

    def test_startup_fails_when_tts_raises(self):
        """If TTS() fails at startup, the app should fail to start."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        mock_tts_cls = MagicMock(side_effect=RuntimeError("model download failed"))
        mock_tts_api = MagicMock()
        mock_tts_api.TTS = mock_tts_cls

        patches = _make_standard_patches(mock_torch, mock_tts_api)

        with patch.dict(sys.modules, patches):
            _cleanup_modules()
            from app.main import app
            with pytest.raises(RuntimeError, match="model download failed"):
                with TestClient(app):
                    pass
            _cleanup_modules()


# ===========================================================================
# _detect_language unit tests
# ===========================================================================
class TestDetectLanguage:
    def test_chinese_text(self):
        assert _detect_language("你好世界") == "zh-cn"

    def test_english_text(self):
        assert _detect_language("hello world") == "en"

    def test_mixed_cjk_english_returns_chinese(self):
        assert _detect_language("hello 你好") == "zh-cn"

    def test_empty_returns_english(self):
        assert _detect_language("") == "en"

    def test_numbers_and_punctuation_returns_english(self):
        assert _detect_language("123 !@#") == "en"

    def test_hiragana_returns_japanese(self):
        assert _detect_language("こんにちは") == "ja"

    def test_katakana_returns_japanese(self):
        assert _detect_language("カタカナ") == "ja"

    def test_kanji_with_hiragana_returns_japanese(self):
        assert _detect_language("東京タワーへ行く") == "ja"

    def test_kanji_only_defaults_to_chinese(self):
        assert _detect_language("東京") == "zh-cn"

    def test_korean_returns_ko(self):
        assert _detect_language("안녕하세요") == "ko"

    def test_korean_with_english_returns_ko(self):
        assert _detect_language("hello 안녕") == "ko"


# ===========================================================================
# _run_xtts unit tests
# ===========================================================================
class TestRunXtts:
    def test_no_output_file_raises_voice_inference_error(self):
        """tts_to_file succeeds but writes nothing → NoOutputError."""
        mock_tts = MagicMock()
        mock_tts.tts_to_file.return_value = None  # no-op, doesn't write file
        with pytest.raises(NoOutputError):
            _run_xtts(mock_tts, b"fake-wav", "hello", "en")


# ===========================================================================
# XTTS v2 inference endpoint tests (Unit 3)
# ===========================================================================
class TestXttsEndpoint:
    def test_queue_full_returns_503(self, client, voice_mocks):
        """Semaphore fully acquired → 503."""
        audio = _make_audio(WEBM_HEADER)
        original = client.app.state.xtts_semaphore
        client.app.state.xtts_semaphore = asyncio.Semaphore(0)
        try:
            voice_mocks.setup()
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.webm", audio, "audio/webm")},
                data={"text": "hello"},
            )
            assert resp.status_code == 503
            assert "忙碌中" in resp.json()["detail"]
        finally:
            client.app.state.xtts_semaphore = original

    def test_audio_too_short_returns_400(self, client, voice_mocks):
        """Duration < 3s → 400."""
        audio = _make_audio(WEBM_HEADER)
        voice_mocks.setup(duration_ms=2000)
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "hello"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "音訊樣本太短，至少需要 3 秒。"

    def test_accept_audio_exactly_3s(self, client, voice_mocks):
        """Duration exactly 3.0s → should pass duration validation."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup(duration_ms=3000)
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "hello"},
        )
        assert resp.status_code == 200

    def test_text_too_long_returns_400(self, client):
        """Text > 500 chars → 400 (rejected before audio conversion)."""
        audio = _make_audio(WEBM_HEADER)
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "a" * 501},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "文字不得超過 500 個字元。"

    def test_accept_text_exactly_500_chars(self, client, voice_mocks):
        """Text exactly 500 chars → should pass validation."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup()
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "a" * 500},
        )
        assert resp.status_code == 200

    def test_model_not_loaded_returns_503(self, client, voice_mocks):
        """tts_model = None → 503."""
        audio = _make_audio(WEBM_HEADER)
        saved = client.app.state.tts_model
        client.app.state.tts_model = None
        try:
            voice_mocks.setup(duration_ms=5000)
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.webm", audio, "audio/webm")},
                data={"text": "hello"},
            )
        finally:
            client.app.state.tts_model = saved
        assert resp.status_code == 503
        assert resp.json()["detail"] == "語音克隆服務尚未就緒。"

    def test_successful_inference_returns_wav(self, client, voice_mocks):
        """Happy path: 200 with synthesised WAV content."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup(duration_ms=5000)
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "hello"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/wav"
        assert resp.content == WAV_STUB
        call_kwargs = client.app.state.tts_model.tts_to_file.call_args[1]
        assert call_kwargs["language"] == "en"

    def test_language_detection_passed_to_tts(self, client, voice_mocks):
        """_detect_language result must be forwarded to tts_to_file(language=...)."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup(duration_ms=5000)
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "你好世界"},
        )
        assert resp.status_code == 200
        call_kwargs = client.app.state.tts_model.tts_to_file.call_args[1]
        assert call_kwargs["language"] == "zh-cn"

    def test_xtts_value_error_returns_422(self, client, voice_mocks):
        """XTTS raises ValueError → 422."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = ValueError("audio too short")
        voice_mocks.setup(duration_ms=5000)
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "hello"},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"] == "音訊樣本太短，無法進行語音克隆。"

    def test_xtts_oom_returns_503(self, client, voice_mocks):
        """XTTS raises OutOfMemoryError → 503."""
        audio = _make_audio(WEBM_HEADER)

        class OutOfMemoryError(Exception):
            pass

        client.app.state.tts_model.tts_to_file.side_effect = OutOfMemoryError("CUDA OOM")
        with patch("app.routes.voice.CudaOOMError", OutOfMemoryError):
            voice_mocks.setup(duration_ms=5000)
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.webm", audio, "audio/webm")},
                data={"text": "hello"},
            )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "語音克隆服務資源不足，請稍後再試。"

    def test_xtts_oom_when_torch_missing_raises(self, client, voice_mocks):
        """When CudaOOMError is None (no torch), OOM propagates as 500."""
        audio = _make_audio(WEBM_HEADER)

        class OutOfMemoryError(Exception):
            pass

        client.app.state.tts_model.tts_to_file.side_effect = OutOfMemoryError("CUDA OOM")
        with patch("app.routes.voice.CudaOOMError", None):
            voice_mocks.setup(duration_ms=5000)
            client._transport.raise_server_exceptions = False
            try:
                resp = client.post(
                    "/api/clone-voice",
                    files={"file": ("rec.webm", audio, "audio/webm")},
                    data={"text": "hello"},
                )
                assert resp.status_code == 500
            finally:
                client._transport.raise_server_exceptions = True

    def test_xtts_no_output_returns_503(self, client, voice_mocks):
        """tts_to_file produces no file → 503."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.return_value = None  # no-op
        voice_mocks.setup(duration_ms=5000)
        resp = client.post(
            "/api/clone-voice",
            files={"file": ("rec.webm", audio, "audio/webm")},
            data={"text": "hello"},
        )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "語音合成未產生輸出檔案。"

    def test_xtts_unexpected_error_raises(self, client, voice_mocks):
        """Unexpected RuntimeError propagates as 500."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = RuntimeError("unexpected")
        voice_mocks.setup(duration_ms=5000)
        client._transport.raise_server_exceptions = False
        try:
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.webm", audio, "audio/webm")},
                data={"text": "hello"},
            )
            assert resp.status_code == 500
        finally:
            client._transport.raise_server_exceptions = True


# ===========================================================================
# Job storage tests
# ===========================================================================
class TestJobStorage:
    def test_success_creates_files_and_returns_job_id(self, client, voice_mocks, tmp_path):
        """Successful request stores original audio, text, and cloned output."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup()
        with patch("app.routes.voice.get_storage_root", return_value=tmp_path):
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.webm", audio, "audio/webm")},
                data={"text": "hello"},
            )
        assert resp.status_code == 200
        job_id = resp.headers["x-job-id"]
        assert len(job_id) == 36  # UUID format

        input_dir = tmp_path / "input" / job_id
        output_dir = tmp_path / "output" / job_id
        assert (input_dir / "original.webm").read_bytes() == audio
        assert (input_dir / "text.txt").read_text(encoding="utf-8") == "hello"
        assert (output_dir / "cloned.wav").read_bytes() == WAV_STUB

    def test_stores_original_bytes_not_wav(self, client, voice_mocks, tmp_path):
        """Input file should be the raw upload, not the WAV-converted version."""
        audio = _make_audio(OGG_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup()
        with patch("app.routes.voice.get_storage_root", return_value=tmp_path):
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.ogg", audio, "audio/ogg")},
                data={"text": "hello"},
            )
        assert resp.status_code == 200
        job_id = resp.headers["x-job-id"]
        stored = (tmp_path / "input" / job_id / "original.ogg").read_bytes()
        assert stored == audio

    def test_storage_failure_still_returns_audio(self, client, voice_mocks, tmp_path):
        """Storage write error is logged but response still succeeds."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup()
        with patch("app.routes.voice.get_storage_root", side_effect=OSError("disk full")):
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.webm", audio, "audio/webm")},
                data={"text": "hello"},
            )
        assert resp.status_code == 200
        assert resp.content == WAV_STUB
        assert "x-job-id" in resp.headers

    def test_no_files_on_validation_failure(self, client, tmp_path):
        """Validation failure (bad magic bytes) should not create storage dirs."""
        fake = b"\x00" * 1024
        with patch("app.routes.voice.get_storage_root", return_value=tmp_path):
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.webm", fake, "audio/webm")},
                data={"text": "hello"},
            )
        assert resp.status_code == 415
        assert not (tmp_path / "input").exists()
        assert not (tmp_path / "output").exists()

    def test_no_files_on_inference_failure(self, client, voice_mocks, tmp_path):
        """Inference failure should not create storage dirs."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.return_value = None  # no output
        voice_mocks.setup()
        with patch("app.routes.voice.get_storage_root", return_value=tmp_path):
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.webm", audio, "audio/webm")},
                data={"text": "hello"},
            )
        assert resp.status_code == 503
        assert not (tmp_path / "input").exists()
        assert not (tmp_path / "output").exists()

    def test_text_stored_correctly(self, client, voice_mocks, tmp_path):
        """Text parameter with unicode should be stored correctly."""
        audio = _make_audio(WEBM_HEADER)
        client.app.state.tts_model.tts_to_file.side_effect = _make_synth_side_effect(WAV_STUB)
        voice_mocks.setup()
        with patch("app.routes.voice.get_storage_root", return_value=tmp_path):
            resp = client.post(
                "/api/clone-voice",
                files={"file": ("rec.webm", audio, "audio/webm")},
                data={"text": "你好世界"},
            )
        assert resp.status_code == 200
        job_id = resp.headers["x-job-id"]
        stored_text = (tmp_path / "input" / job_id / "text.txt").read_text(encoding="utf-8")
        assert stored_text == "你好世界"
