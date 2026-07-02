import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import httpx
from loguru import logger
import yt_dlp

try:
    from .base_extractor import BaseExtractor
except ImportError:
    from base_extractor import BaseExtractor

class YoutubeExtractor(BaseExtractor):
    """Specialized extractor for YouTube using yt-dlp library."""

    def __init__(self):
        self.url = ""
        self.title = ""
        self.thumbnail = ""
        self.duration = 0.0
        self.uploader = "YouTube Video"
        self.description = ""
        self.formats: List[Dict[str, Any]] = []

    def validate_url(self, url: str) -> bool:
        """Returns True if the URL is a YouTube domain."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return "youtube.com" in domain or "youtu.be" in domain

    async def analyze(self, url: str) -> None:
        self.url = url
        self.formats = []

        logger.info(f"Analyzing YouTube URL using yt-dlp: {url}")
        
        loop = asyncio.get_running_loop()
        
        def extract():
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "youtube_include_dash_manifest": False,
                "youtube_include_hls_manifest": False
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await loop.run_in_executor(None, extract)
            
            self.title = info.get("title") or "YouTube Video"
            self.uploader = info.get("uploader") or "YouTube Uploader"
            self.duration = float(info.get("duration") or 0.0)
            self.description = info.get("description") or ""
            self.thumbnail = info.get("thumbnail") or f"https://img.youtube.com/vi/{info.get('id')}/maxresdefault.jpg"

            raw_formats = info.get("formats", [])
            for raw_fmt in raw_formats:
                stream_url = raw_fmt.get("url")
                if not stream_url:
                    continue

                resolution = raw_fmt.get("resolution") or raw_fmt.get("quality_label")
                if not resolution:
                    if raw_fmt.get("vcodec") == "none":
                        resolution = "audio"
                    else:
                        resolution = f"{raw_fmt.get('width', 0)}x{raw_fmt.get('height', 0)}"

                is_audio = raw_fmt.get("vcodec") == "none"
                ext = raw_fmt.get("ext") or "mp4"
                
                # Combine headers
                headers = raw_fmt.get("http_headers") or {}
                
                self.formats.append({
                    "format_id": f"yt_{raw_fmt.get('format_id')}",
                    "url": stream_url,
                    "resolution": resolution,
                    "ext": ext,
                    "vcodec": raw_fmt.get("vcodec") or "none",
                    "acodec": raw_fmt.get("acodec") or "none",
                    "vbitrate": int(raw_fmt.get("tbr") or 0) or None,
                    "abitrate": int(raw_fmt.get("abr") or 0) or None,
                    "fps": raw_fmt.get("fps"),
                    "filesize": raw_fmt.get("filesize") or raw_fmt.get("filesize_approx") or None,
                    "headers": headers,
                    "is_dash": is_audio or (raw_fmt.get("acodec") == "none"),
                    "is_audio_only": is_audio,
                    "is_video_only": not is_audio and raw_fmt.get("acodec") == "none"
                })
                
        except Exception as e:
            logger.error(f"yt-dlp extraction failed: {e}")
            raise ValueError(f"Failed to analyze YouTube page: {e}")

    async def download(
        self,
        format_id: str,
        save_path: str,
        progress_callback: Optional[Any] = None,
        cancel_token: Optional[Any] = None
    ) -> None:
        """Downloads the format using standard streaming HTTP logic."""
        fmt = next((f for f in self.formats if f["format_id"] == format_id), None)
        if not fmt:
            raise ValueError(f"Unknown format ID: {format_id}")
            
        url = fmt["url"]
        headers = fmt.get("headers") or {}
        
        logger.info(f"Downloading YouTube stream using resolved yt-dlp URL to {save_path}")
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        import time
        start_time = time.time()
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            async with client.stream("GET", url, headers=headers) as response:
                if response.status_code != 200:
                    raise ValueError(f"Server returned HTTP status {response.status_code}")
                    
                total_bytes = int(response.headers.get("content-length", 0))
                downloaded_bytes = 0
                
                with open(save_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 128):
                        if cancel_token and cancel_token.is_cancelled:
                            raise asyncio.CancelledError("Download cancelled.")
                            
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        
                        elapsed = time.time() - start_time
                        speed = downloaded_bytes / elapsed if elapsed > 0 else 0
                        progress = (downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0.0
                        
                        if progress_callback:
                            try:
                                progress_callback({
                                    "status": "downloading",
                                    "downloaded_bytes": downloaded_bytes,
                                    "total_bytes": total_bytes or downloaded_bytes,
                                    "speed": speed,
                                    "progress": progress
                                })
                            except Exception as e:
                                logger.error(f"Callback error in YouTube download: {e}")

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
