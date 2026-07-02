"""
Tests for ExtractorManager — dynamic loading, URL routing, and fallback logic.
"""
import sys
import pytest
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.extractors.extractor_manager import ExtractorManager
from app.extractors.base_extractor import BaseExtractor


class TestExtractorManagerLoading:
    def test_load_all_registers_builtins(self):
        """After load_all(), at least the built-in extractors should be present."""
        mgr = ExtractorManager()
        mgr.load_all()
        names = [cls.__name__ for cls in mgr.extractors]
        assert "MockExtractor" in names
        assert "GenericExtractor" in names

    def test_load_all_count_is_positive(self):
        """load_all() must register at least one extractor."""
        mgr = ExtractorManager()
        mgr.load_all()
        assert len(mgr.extractors) >= 1

    def test_load_all_idempotent(self):
        """Calling load_all() twice should not duplicate entries."""
        mgr = ExtractorManager()
        mgr.load_all()
        count_first = len(mgr.extractors)
        mgr.load_all()
        assert len(mgr.extractors) == count_first


class TestExtractorManagerURLRouting:
    def setup_method(self):
        self.mgr = ExtractorManager()
        self.mgr.load_all()

    def test_mock_url_uses_mock_extractor(self):
        """mockvideo.com URLs should be routed to MockExtractor."""
        extractor = self.mgr.get_extractor_for_url("https://mockvideo.com/watch/123")
        assert extractor.__class__.__name__ == "MockExtractor"

    def test_youtube_url_uses_youtube_extractor(self):
        """youtube.com URLs should use YoutubeExtractor when registered."""
        names = [cls.__name__ for cls in self.mgr.extractors]
        if "YoutubeExtractor" not in names:
            pytest.skip("YoutubeExtractor not registered")
        extractor = self.mgr.get_extractor_for_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert extractor.__class__.__name__ == "YoutubeExtractor"

    def test_unknown_url_falls_back_to_generic(self):
        """An unrecognised URL should fall back to GenericExtractor."""
        extractor = self.mgr.get_extractor_for_url("https://someobscuresite.example.org/video")
        assert extractor.__class__.__name__ == "GenericExtractor"

    def test_no_extractors_raises_value_error(self, monkeypatch):
        """If no extractors are loaded at all, get_extractor_for_url should raise."""
        empty_mgr = ExtractorManager()
        # Do NOT call load_all — extractors list stays empty
        with pytest.raises(ValueError, match="No extractor found"):
            empty_mgr.get_extractor_for_url("https://example.com/video")

    def test_returned_extractor_is_base_extractor_subclass(self):
        """Whatever extractor is returned, it must be a BaseExtractor subclass."""
        extractor = self.mgr.get_extractor_for_url("https://mockvideo.com/watch/1")
        assert isinstance(extractor, BaseExtractor)
