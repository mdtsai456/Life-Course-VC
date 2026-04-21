"""Tests for /api/jobs/{id} and /api/jobs/{id}/audio endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import patch


def _seed_job(storage_root, job_id: str, content: bytes = b"RIFFwave"):
    out = storage_root / "output" / job_id
    out.mkdir(parents=True)
    (out / "cloned.wav").write_bytes(content)


class TestGetJob:
    def test_valid_completed_job(self, client, tmp_path):
        job_id = str(uuid.uuid4())
        with patch("app.routes.jobs.get_storage_root", return_value=tmp_path):
            _seed_job(tmp_path, job_id)
            resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["job_id"] == job_id
        assert body["status"] == "completed"
        assert body["audio_url"] == f"/api/jobs/{job_id}/audio"
        assert body["size_bytes"] == len(b"RIFFwave")
        assert "created_at" in body

    def test_unknown_uuid_returns_404(self, client, tmp_path):
        with patch("app.routes.jobs.get_storage_root", return_value=tmp_path):
            resp = client.get(f"/api/jobs/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_malformed_id_returns_404(self, client):
        resp = client.get("/api/jobs/not-a-uuid")
        assert resp.status_code == 404

    def test_path_traversal_blocked(self, client, tmp_path):
        # Attempt to probe outside storage root with traversal-like id.
        # FastAPI path param doesn't match "/" so "../../etc" won't reach handler,
        # but UUID validation still rejects non-UUID strings.
        with patch("app.routes.jobs.get_storage_root", return_value=tmp_path):
            resp = client.get("/api/jobs/..")
        assert resp.status_code == 404


class TestGetJobAudio:
    def test_downloads_wav(self, client, tmp_path):
        job_id = str(uuid.uuid4())
        payload = b"RIFF\x00\x00\x00\x00WAVEfmt data"
        with patch("app.routes.jobs.get_storage_root", return_value=tmp_path):
            _seed_job(tmp_path, job_id, payload)
            resp = client.get(f"/api/jobs/{job_id}/audio")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/wav"
        assert resp.content == payload

    def test_unknown_job_returns_404(self, client, tmp_path):
        with patch("app.routes.jobs.get_storage_root", return_value=tmp_path):
            resp = client.get(f"/api/jobs/{uuid.uuid4()}/audio")
        assert resp.status_code == 404

    def test_malformed_id_returns_404(self, client):
        resp = client.get("/api/jobs/xyz/audio")
        assert resp.status_code == 404
