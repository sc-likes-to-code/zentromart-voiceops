"""Tests for root batch runner run.py."""
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.voice import VoiceTurnResult


def test_run_batch_cli_help():
    """run.py --help must execute cleanly and return exit code 0."""
    res = subprocess.run(
        [sys.executable, "run.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "usage: python run.py" in res.stdout
    assert "audio_folder" in res.stdout


def test_run_batch_cli_nonexistent_folder(tmp_path: Path):
    """run.py with nonexistent directory must exit with code 1."""
    res = subprocess.run(
        [sys.executable, "run.py", str(tmp_path / "nonexistent_dir")],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "not found or is not a directory" in res.stderr


def test_run_batch_cli_empty_folder(tmp_path: Path):
    """run.py with empty directory must exit with code 1 and inform user."""
    empty_dir = tmp_path / "empty_audio"
    empty_dir.mkdir()
    res = subprocess.run(
        [sys.executable, "run.py", str(empty_dir)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "No supported audio files" in res.stderr
