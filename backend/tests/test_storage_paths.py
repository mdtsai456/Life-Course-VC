"""Tests for storage_paths and get_storage_root."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.config import get_storage_root
from app.storage_paths import ensure_job_dirs, job_input_dir, job_output_dir


class TestGetStorageRoot:
    def test_returns_path_from_env_var(self, tmp_path):
        with patch.dict("os.environ", {"STORAGE_ROOT": str(tmp_path)}):
            result = get_storage_root()
        assert result == tmp_path.resolve()
        assert isinstance(result, Path)

    def test_returns_default_when_unset(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("STORAGE_ROOT", None)
            result = get_storage_root()
        assert result == Path("./storage").resolve()


class TestJobInputDir:
    def test_returns_correct_path(self, tmp_path):
        result = job_input_dir(tmp_path, "abc-123")
        assert result == tmp_path / "input" / "abc-123"


class TestJobOutputDir:
    def test_returns_correct_path(self, tmp_path):
        result = job_output_dir(tmp_path, "abc-123")
        assert result == tmp_path / "output" / "abc-123"


class TestEnsureJobDirs:
    def test_creates_directories_and_returns_paths(self, tmp_path):
        input_dir, output_dir = ensure_job_dirs(tmp_path, "job-001")
        assert input_dir == tmp_path / "input" / "job-001"
        assert output_dir == tmp_path / "output" / "job-001"
        assert input_dir.is_dir()
        assert output_dir.is_dir()

    def test_succeeds_when_dirs_already_exist(self, tmp_path):
        ensure_job_dirs(tmp_path, "job-001")
        # Call again — should not raise
        input_dir, output_dir = ensure_job_dirs(tmp_path, "job-001")
        assert input_dir.is_dir()
        assert output_dir.is_dir()
