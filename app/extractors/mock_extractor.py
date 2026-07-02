import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
try:
    from .base_extractor import BaseExtractor
except ImportError:
    from base_extractor import BaseExtractor


class MockExtractor(BaseExtractor):
    """Mock extractor for testing and UI demonstrations."""

    def __init__(self):
        self.url = ""
        self.title = "Mock Demo Video - How to Program in Python"
        self.thumbnail = "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5"
        self.duration = 180.0
        self.uploader = "Antigravity Devs"
        self.description = "A comprehensive mock tutorial showing how to write clean code in Python 3.12."
        self.formats = [
            {
                "format_id": "1080p_mp4",
                "url": "https://mockvideo.com/streams/1080p.mp4",
                "resolution": "1920x1080",
                "ext": "mp4",
                "vcodec": "h264",
                "acodec": "aac",
                "vbitrate": 4500,
                "abitrate": 192,
                "fps": 30,
                "filesize": 1024 * 1024 * 50,  # 50 MB
                "headers": {},
                "is_dash": False,
                "is_audio_only": False,
                "is_video_only": False
            },
            {
                "format_id": "720p_mp4",
                "url": "https://mockvideo.com/streams/720p.mp4",
                "resolution": "1280x720",
                "ext": "mp4",
                "vcodec": "h264",
                "acodec": "aac",
                "vbitrate": 2200,
                "abitrate": 128,
                "fps": 30,
                "filesize": 1024 * 1024 * 25,  # 25 MB
                "headers": {},
                "is_dash": False,
                "is_audio_only": False,
                "is_video_only": False
            },
            {
                "format_id": "audio_only",
                "url": "https://mockvideo.com/streams/audio.mp3",
                "resolution": "audio",
                "ext": "mp3",
                "vcodec": "none",
                "acodec": "mp3",
                "vbitrate": 0,
                "abitrate": 320,
                "fps": 0,
                "filesize": 1024 * 1024 * 7,  # 7 MB
                "headers": {},
                "is_dash": False,
                "is_audio_only": True,
                "is_video_only": False
            }
        ]

    def validate_url(self, url: str) -> bool:
        """Validates if the URL belongs to the mock site."""
        return "mockvideo.com" in url or "example.com/mock" in url

    async def analyze(self, url: str) -> None:
        """Simulates analyzing the page by adding a small async delay."""
        self.url = url
        logger.debug(f"Mock-analyzing URL: {url}")
        await asyncio.sleep(0.5)  # Simulate network latency
        logger.debug("Mock analysis complete.")

    def get_title(self) -> str:
        return self.title

    def get_thumbnail(self) -> str:
        return self.thumbnail

    def get_duration(self) -> float:
        return self.duration

    def get_uploader(self) -> str:
        return self.uploader

    def get_description(self) -> str:
        return self.description

    def get_available_formats(self) -> List[Dict[str, Any]]:
        return self.formats

    async def download(
        self,
        format_id: str,
        save_path: str,
        progress_callback: Optional[Any] = None,
        cancel_token: Optional[Any] = None
    ) -> None:
        """Simulates downloading by writing dummy data and triggering progress callbacks."""
        logger.info(f"Starting mock download of format {format_id} to {save_path}")
        
        # Find format
        fmt = next((f for f in self.formats if f["format_id"] == format_id), self.formats[0])
        total_size = fmt["filesize"] or (1024 * 1024 * 10)
        
        chunk_size = 1024 * 100  # 100KB chunks
        downloaded = 0
        
        # Ensure parent folder exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        
        with open(save_path, "wb") as f:
            while downloaded < total_size:
                if cancel_token and cancel_token.is_cancelled:
                    logger.info("Mock download cancelled.")
                    raise asyncio.CancelledError("Download cancelled by user.")
                
                # Simulate small latency for downloads
                await asyncio.sleep(0.05)
                
                # Write some dummy bytes
                f.write(b"\0" * chunk_size)
                downloaded += chunk_size
                
                # Cap downloaded bytes
                if downloaded > total_size:
                    downloaded = total_size
                    
                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0
                
                if progress_callback:
                    # Trigger the progress callback
                    try:
                        progress_callback({
                            "status": "downloading",
                            "downloaded_bytes": downloaded,
                            "total_bytes": total_size,
                            "speed": speed,
                            "progress": (downloaded / total_size) * 100
                        })
                    except Exception as e:
                        logger.error(f"Error executing progress callback: {e}")

        logger.info(f"Mock download completed successfully: {save_path}")
