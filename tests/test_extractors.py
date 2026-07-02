"""
Tests for individual extractor plugins — MockExtractor (offline) and
GenericExtractor (with mocked HTTP responses).
"""
import sys
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.extractors.mock_extractor import MockExtractor

pytestmark = pytest.mark.asyncio


# ──────────────────────────────────────────────
#  MockExtractor Tests (no network required)
# ──────────────────────────────────────────────

class TestMockExtractor:
    def setup_method(self):
        self.ext = MockExtractor()

    def test_validate_url_accepts_mockvideo(self):
        assert self.ext.validate_url("https://mockvideo.com/watch/1") is True

    def test_validate_url_accepts_example_mock(self):
        assert self.ext.validate_url("https://example.com/mock/video") is True

    def test_validate_url_rejects_youtube(self):
        assert self.ext.validate_url("https://www.youtube.com/watch?v=abc") is False

    async def test_analyze_populates_title(self):
        await self.ext.analyze("https://mockvideo.com/watch/test")
        assert len(self.ext.get_title()) > 0

    async def test_analyze_stores_url(self):
        url = "https://mockvideo.com/watch/xyz"
        await self.ext.analyze(url)
        assert self.ext.url == url

    def test_get_available_formats_returns_list(self):
        formats = self.ext.get_available_formats()
        assert isinstance(formats, list)
        assert len(formats) > 0

    def test_format_has_required_keys(self):
        required = {"format_id", "url", "resolution", "ext", "vcodec", "acodec"}
        for fmt in self.ext.get_available_formats():
            assert required.issubset(fmt.keys()), f"Format {fmt} missing required keys"

    def test_audio_only_format_exists(self):
        formats = self.ext.get_available_formats()
        audio = [f for f in formats if f.get("is_audio_only")]
        assert len(audio) >= 1

    def test_get_uploader_not_empty(self):
        assert len(self.ext.get_uploader()) > 0

    def test_get_duration_positive(self):
        assert self.ext.get_duration() > 0

    def test_get_thumbnail_is_url(self):
        thumb = self.ext.get_thumbnail()
        assert thumb.startswith("http")

    async def test_download_creates_file(self, tmp_path):
        """MockExtractor.download() should write a non-empty file."""
        await self.ext.analyze("https://mockvideo.com/watch/1")
        fmt_id = self.ext.get_available_formats()[0]["format_id"]
        dest = str(tmp_path / "output.mp4")
        await self.ext.download(fmt_id, dest)
        output = Path(dest)
        assert output.exists()
        assert output.stat().st_size > 0

    async def test_download_fires_progress_callbacks(self, tmp_path):
        """Progress callbacks should be called at least once during download."""
        await self.ext.analyze("https://mockvideo.com/watch/1")
        fmt_id = self.ext.get_available_formats()[1]["format_id"]
        dest = str(tmp_path / "output2.mp4")

        fired = []
        def cb(metrics):
            fired.append(metrics)

        await self.ext.download(fmt_id, dest, progress_callback=cb)
        assert len(fired) > 0
        assert "progress" in fired[-1]
        assert fired[-1]["progress"] == pytest.approx(100.0, abs=5)

    async def test_download_respects_cancel_token(self, tmp_path):
        """A pre-cancelled token should abort the download immediately."""
        await self.ext.analyze("https://mockvideo.com/watch/1")
        fmt_id = self.ext.get_available_formats()[0]["format_id"]
        dest = str(tmp_path / "cancelled.mp4")

        cancel = MagicMock()
        cancel.is_cancelled = True  # Already cancelled before starting

        with pytest.raises((asyncio.CancelledError, Exception)):
            await self.ext.download(fmt_id, dest, cancel_token=cancel)


# ──────────────────────────────────────────────
#  GenericExtractor Tests (mocked HTTP)
# ──────────────────────────────────────────────

class TestGenericExtractorValidation:
    def test_import_succeeds(self):
        """GenericExtractor should be importable without errors."""
        from app.extractors.generic_extractor import GenericExtractor
        ext = GenericExtractor()
        assert ext is not None

    def test_accepts_http_url(self):
        from app.extractors.generic_extractor import GenericExtractor
        ext = GenericExtractor()
        # GenericExtractor is a fallback; validate_url returns True for any HTTP URL
        assert ext.validate_url("https://any-site.com/video") is True

    def test_rejects_non_http(self):
        from app.extractors.generic_extractor import GenericExtractor
        ext = GenericExtractor()
        # Non-HTTP should return False
        assert ext.validate_url("ftp://files.example.com/video.mp4") is False
