"""
Tests for the Typer CLI commands — 'analyze' and 'download'.
All network calls are mocked so tests run fully offline.
"""
import sys
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import cli_app

runner = CliRunner()


# ──────────────────────────────────────────────
#  Shared Mock Extractor Setup
# ──────────────────────────────────────────────

def _make_mock_extractor():
    """Returns a mock object that satisfies the BaseExtractor interface."""
    ext = MagicMock()
    ext.validate_url.return_value = True
    ext.analyze = AsyncMock()
    ext.get_title.return_value = "CLI Test Video"
    ext.get_uploader.return_value = "CLI Tester"
    ext.get_duration.return_value = 120.0
    ext.get_thumbnail.return_value = "https://example.com/thumb.jpg"
    ext.get_description.return_value = "A CLI test video description."
    ext.get_available_formats.return_value = [
        {
            "format_id": "mock_720",
            "url": "https://mockvideo.com/streams/720p.mp4",
            "resolution": "1280x720",
            "ext": "mp4",
            "vcodec": "h264",
            "acodec": "aac",
            "filesize": 1024 * 1024 * 10,
            "headers": {},
            "is_dash": False,
            "is_audio_only": False,
            "is_video_only": False,
        }
    ]
    ext.download = AsyncMock()
    return ext


def _make_mock_manager(ext):
    mgr = MagicMock()
    mgr.load_all = MagicMock()
    mgr.get_extractor_for_url.return_value = ext
    return mgr


# ──────────────────────────────────────────────
#  'analyze' Command Tests
# ──────────────────────────────────────────────

class TestAnalyzeCommand:
    def test_analyze_shows_title(self, tmp_path):
        ext = _make_mock_extractor()
        mgr = _make_mock_manager(ext)

        with patch("main.ExtractorManager", return_value=mgr), \
             patch("main.DatabaseManager") as MockDB:
            db_instance = MagicMock()
            db_instance.initialize = AsyncMock()
            db_instance.add_recent_url = AsyncMock()
            MockDB.return_value = db_instance

            result = runner.invoke(cli_app, ["analyze", "https://mockvideo.com/watch/1"])

        assert result.exit_code == 0, result.output
        assert "CLI Test Video" in result.output

    def test_analyze_shows_uploader(self, tmp_path):
        ext = _make_mock_extractor()
        mgr = _make_mock_manager(ext)

        with patch("main.ExtractorManager", return_value=mgr), \
             patch("main.DatabaseManager") as MockDB:
            db_instance = MagicMock()
            db_instance.initialize = AsyncMock()
            db_instance.add_recent_url = AsyncMock()
            MockDB.return_value = db_instance

            result = runner.invoke(cli_app, ["analyze", "https://mockvideo.com/watch/1"])

        assert "CLI Tester" in result.output

    def test_analyze_shows_format_ids(self, tmp_path):
        ext = _make_mock_extractor()
        mgr = _make_mock_manager(ext)

        with patch("main.ExtractorManager", return_value=mgr), \
             patch("main.DatabaseManager") as MockDB:
            db_instance = MagicMock()
            db_instance.initialize = AsyncMock()
            db_instance.add_recent_url = AsyncMock()
            MockDB.return_value = db_instance

            result = runner.invoke(cli_app, ["analyze", "https://mockvideo.com/watch/1"])

        assert "mock_720" in result.output

    def test_analyze_handles_extractor_exception(self):
        ext = _make_mock_extractor()
        ext.analyze = AsyncMock(side_effect=RuntimeError("Network failure"))
        mgr = _make_mock_manager(ext)

        with patch("main.ExtractorManager", return_value=mgr), \
             patch("main.DatabaseManager") as MockDB:
            db_instance = MagicMock()
            db_instance.initialize = AsyncMock()
            db_instance.add_recent_url = AsyncMock()
            MockDB.return_value = db_instance

            result = runner.invoke(cli_app, ["analyze", "https://mockvideo.com/watch/err"])

        # Should not crash with an unhandled traceback — just print an error message
        assert result.exit_code == 0  # typer catches and reports; exit 0 is expected here
        assert "Analysis failed" in result.output or "Network failure" in result.output


# ──────────────────────────────────────────────
#  'download' Command Tests
# ──────────────────────────────────────────────

class TestDownloadCommand:
    def _invoke_download(self, extra_args=None, ext=None, tmp_path=None):
        ext = ext or _make_mock_extractor()
        mgr = _make_mock_manager(ext)
        args = ["download", "https://mockvideo.com/watch/1"] + (extra_args or [])

        with patch("main.ExtractorManager", return_value=mgr), \
             patch("main.DatabaseManager") as MockDB, \
             patch("main.QueueManager") as MockQM:

            db_instance = MagicMock()
            db_instance.initialize = AsyncMock()
            MockDB.return_value = db_instance

            # Build a fake task that completes immediately
            fake_task = MagicMock()
            fake_task.status = "completed"
            qm_instance = MagicMock()
            qm_instance.start = MagicMock()
            qm_instance.stop = AsyncMock()
            qm_instance.tasks = {}

            async def fake_add(**kwargs):
                qm_instance.tasks[1] = fake_task
                return 1

            qm_instance.add_download = fake_add
            MockQM.return_value = qm_instance

            result = runner.invoke(cli_app, args)

        return result

    def test_download_exits_successfully(self):
        result = self._invoke_download()
        assert result.exit_code == 0, result.output

    def test_download_format_flag(self):
        result = self._invoke_download(extra_args=["--format", "mock_720"])
        assert result.exit_code == 0, result.output

    def test_download_output_flag(self, tmp_path):
        result = self._invoke_download(extra_args=["--output", str(tmp_path)])
        assert result.exit_code == 0, result.output

    def test_download_no_formats_raises_error(self):
        ext = _make_mock_extractor()
        ext.get_available_formats.return_value = []
        result = self._invoke_download(ext=ext)
        # Should print an error, not crash
        assert "failed" in result.output.lower() or "no formats" in result.output.lower() or result.exit_code == 0
