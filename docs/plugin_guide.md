# Extractor Plugin Development Guide

This guide details how to implement and install custom extractor plugins for **Video Downloader Pro**.

---

## 1. Overview

Each supported website is treated as a separate extractor plugin. The core application scans two locations on launch:
1. Built-in folder: `app/extractors/`
2. External plugin folder: `~/.video_downloader_pro/plugins/` (or package `app/plugins/` directory)

Any python module placed in these folders containing a class that implements `BaseExtractor` will be dynamically loaded and registered.

---

## 2. Interface Template

Create a new file, e.g. `mywebsite_extractor.py`, and implement the required abstract methods:

```python
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.extractors.base_extractor import BaseExtractor

class MyWebsiteExtractor(BaseExtractor):
    """Custom extractor for mywebsite.com."""

    def validate_url(self, url: str) -> bool:
        """Return True if url belongs to mywebsite.com."""
        return "mywebsite.com" in url

    async def analyze(self, url: str) -> None:
        """Fetch the page and extract available formats and video metadata."""
        # Perform HTTP requests, BeautifulSoup parsing, etc.
        self._title = "Video Title"
        self._thumb = "https://mywebsite.com/thumb.jpg"
        self._duration = 320.0
        self._uploader = "AuthorName"
        self._desc = "Detailed video description."
        
        # Populate formats list
        self._formats = [{
            "format_id": "720p_stream",
            "url": "https://mywebsite.com/direct_video_720p.mp4",
            "resolution": "1280x720",
            "ext": "mp4",
            "vcodec": "h264",
            "acodec": "aac",
            "vbitrate": 1500,
            "filesize": 1024 * 1024 * 35,  # Optional size
            "is_dash": False,
            "is_audio_only": False,
            "is_video_only": False
        }]

    def get_title(self) -> str:
        return self._title

    def get_thumbnail(self) -> str:
        return self._thumb

    def get_duration(self) -> float:
        return self._duration

    def get_uploader(self) -> str:
        return self._uploader

    def get_description(self) -> str:
        return self._desc

    def get_available_formats(self) -> List[Dict[str, Any]]:
        return self._formats

    async def download(
        self,
        format_id: str,
        save_path: str,
        progress_callback: Optional[Any] = None,
        cancel_token: Optional[Any] = None
    ) -> None:
        """Implements custom stream downloads if direct HTTP is insufficient."""
        # Typically, you can delegate direct HTTP streams to the base HTTP downloader.
        # But if you need decryption, custom token generation, or HLS downloading,
        # implement it here.
        pass
```

---

## 3. Installation

1. Copy your python script into the user-specific plugins folder at `~/.video_downloader_pro/plugins/`.
2. Launch the application.
3. Verify that the console log outputs:
   `Successfully registered extractor: MyWebsiteExtractor`
