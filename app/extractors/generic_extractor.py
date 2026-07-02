import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup
from loguru import logger
try:
    from .base_extractor import BaseExtractor
except ImportError:
    from base_extractor import BaseExtractor


class GenericExtractor(BaseExtractor):
    """Fallback extractor that parses general HTML pages for media tags or handles direct media URLs."""

    def __init__(self):
        self.url = ""
        self.title = ""
        self.thumbnail = ""
        self.duration = 0.0
        self.uploader = "Webpage Content"
        self.description = ""
        self.formats: List[Dict[str, Any]] = []

    def _build_default_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def validate_url(self, url: str) -> bool:
        """Accepts any valid http or https URL."""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    async def analyze(self, url: str) -> None:
        """Analyzes a URL to extract media and metadata."""
        self.url = url
        self.formats = []
        
        # Check if URL is a direct media file
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        direct_extensions = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".mp3", ".ogg", ".wav", ".aac")
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            if path.endswith(direct_extensions):
                await self._process_direct_url(client, url)
                return

            # Otherwise, fetch HTML page
            logger.debug(f"Fetching HTML page: {url}")
            try:
                response = await client.get(url, headers=self._build_default_headers(referer=url))
            except Exception as e:
                logger.error(f"Failed to fetch webpage: {e}")
                raise ConnectionError(f"Failed to connect to the server: {e}")

            # Check if response content type is actually media
            content_type = response.headers.get("content-type", "").lower()
            if "video/" in content_type or "audio/" in content_type:
                await self._process_direct_url(client, url)
                return

            if response.status_code != 200:
                raise ValueError(f"HTTP Error {response.status_code} while fetching page")

            # Parse HTML
            await self._parse_html(client, response.text)

    async def _process_direct_url(self, client: httpx.AsyncClient, url: str) -> None:
        """Processes a direct media URL to retrieve basic file metadata."""
        logger.info(f"Processing direct media URL: {url}")
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name or "direct_media"
        self.title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
        self.thumbnail = ""
        self.duration = 0.0
        self.uploader = parsed_url.netloc
        self.description = f"Direct downloadable stream from {url}"

        # Fetch size/type via HEAD request
        filesize = None
        ext = os.path.splitext(filename)[1].replace(".", "") or "mp4"
        try:
            head_res = await client.head(url)
            if "content-length" in head_res.headers:
                filesize = int(head_res.headers["content-length"])
            content_type = head_res.headers.get("content-type", "")
            if "/" in content_type:
                # e.g., video/mp4 -> mp4
                detected_ext = content_type.split("/")[1]
                if detected_ext in ("mp4", "x-matroska", "webm", "mpeg", "quicktime"):
                    ext = "mkv" if detected_ext == "x-matroska" else detected_ext
        except Exception as e:
            logger.warning(f"Failed to fetch HEAD info for direct URL: {e}")

        is_audio = ext in ("mp3", "wav", "ogg", "aac", "m4a")
        
        self.formats.append({
            "format_id": "direct_stream",
            "url": url,
            "resolution": "audio" if is_audio else "unknown",
            "ext": ext,
            "vcodec": "none" if is_audio else "unknown",
            "acodec": ext if is_audio else "unknown",
            "vbitrate": None,
            "abitrate": None,
            "fps": None,
            "filesize": filesize,
            "headers": self._build_default_headers(referer=self.url),
            "is_dash": False,
            "is_audio_only": is_audio,
            "is_video_only": False
        })

    async def _parse_html(self, client: httpx.AsyncClient, html_content: str) -> None:
        """Parses HTML content for OpenGraph tags, title, and video/source elements."""
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 1. Title Extraction
        og_title = soup.find("meta", property="og:title")
        title_tag = soup.find("title")
        h1_tag = soup.find("h1")
        if og_title and og_title.get("content"):
            self.title = og_title["content"].strip()
        elif title_tag:
            self.title = title_tag.text.strip()
        elif h1_tag:
            self.title = h1_tag.text.strip()
        else:
            self.title = "Extracted Video Webpage"

        # 2. Thumbnail Extraction
        og_image = soup.find("meta", property="og:image")
        link_img = soup.find("link", rel="image_src")
        if og_image and og_image.get("content"):
            self.thumbnail = og_image["content"].strip()
        elif link_img and link_img.get("href"):
            self.thumbnail = link_img["href"].strip()
            
        # 3. Description & Uploader
        og_desc = soup.find("meta", property="og:description")
        desc_meta = soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            self.description = og_desc["content"].strip()
        elif desc_meta and desc_meta.get("content"):
            self.description = desc_meta["content"].strip()
            
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get("content"):
            self.uploader = author_meta["content"].strip()
        else:
            self.uploader = urlparse(self.url).netloc

        # 4. Search for media tags
        # Scan <video> and <audio> tags
        media_tags = soup.find_all(["video", "audio"])
        raw_sources: List[str] = []
        
        for tag in media_tags:
            # Check src attribute on video/audio tag
            if tag.get("src"):
                raw_sources.append(tag["src"])
            # Check child <source> tags
            for src_tag in tag.find_all("source"):
                if src_tag.get("src"):
                    raw_sources.append(src_tag["src"])

        # De-duplicate links while preserving order
        unique_sources: List[str] = []
        for src in raw_sources:
            full_url = urljoin(self.url, src)
            if full_url not in unique_sources:
                unique_sources.append(full_url)

        # Query sizes and content types of unique media links asynchronously
        for idx, src_url in enumerate(unique_sources):
            # Parse extension from URL
            path_parsed = urlparse(src_url)
            ext = os.path.splitext(path_parsed.path)[1].replace(".", "") or "mp4"
            
            is_audio = ext in ("mp3", "wav", "ogg", "aac", "m4a")
            filesize = None
            
            # HEAD request to check size
            try:
                head_res = await client.head(src_url, headers=self._build_default_headers(referer=self.url), timeout=3.0)
                if "content-length" in head_res.headers:
                    filesize = int(head_res.headers["content-length"])
            except Exception:
                pass
                
            self.formats.append({
                "format_id": f"stream_{idx}",
                "url": src_url,
                "resolution": "audio" if is_audio else f"Stream {idx+1}",
                "ext": ext,
                "vcodec": "none" if is_audio else "unknown",
                "acodec": ext if is_audio else "unknown",
                "vbitrate": None,
                "abitrate": None,
                "fps": None,
                "filesize": filesize,
                "headers": self._build_default_headers(referer=self.url),
                "is_dash": False,
                "is_audio_only": is_audio,
                "is_video_only": False
            })

        if not self.formats:
            # Let's inspect page for common video links inside links/anchors if no tags found
            # A simple regex search in hrefs
            anchors = soup.find_all("a", href=True)
            video_pattern = re.compile(r"\.(mp4|mkv|mov|avi|webm|m3u8)(\?.*)?$", re.IGNORECASE)
            idx = 0
            for a in anchors:
                href = a["href"]
                if video_pattern.search(href):
                    full_url = urljoin(self.url, href)
                    if full_url not in [f["url"] for f in self.formats]:
                        ext = video_pattern.search(href).group(1)
                        self.formats.append({
                            "format_id": f"anchor_stream_{idx}",
                            "url": full_url,
                            "resolution": f"Link {idx+1}",
                            "ext": ext,
                            "vcodec": "unknown",
                            "acodec": "unknown",
                            "vbitrate": None,
                            "abitrate": None,
                            "fps": None,
                            "filesize": None,
                            "headers": self._build_default_headers(referer=self.url),
                            "is_dash": False,
                            "is_audio_only": False,
                            "is_video_only": False
                        })
                        idx += 1
                        
        if not self.formats:
            raise ValueError("No downloadable streams or video tags detected on this page.")

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
        """Downloads the chosen format directly via HTTP streaming.
        
        This delegates directly to a file download stream because GenericExtractor uses standard HTTP URLs.
        """
        # Find format
        fmt = next((f for f in self.formats if f["format_id"] == format_id), None)
        if not fmt:
            raise ValueError(f"Unknown format ID: {format_id}")
            
        url = fmt["url"]
        headers = fmt.get("headers") or {}
        
        # Download logic using streaming httpx
        logger.info(f"Downloading {url} to {save_path}")
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        import time
        start_time = time.time()
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            stream_headers = {**self._build_default_headers(referer=self.url), **headers}
            async with client.stream("GET", url, headers=stream_headers) as response:
                if response.status_code != 200:
                    raise ValueError(f"Server returned HTTP status {response.status_code}")
                    
                total_bytes = int(response.headers.get("content-length", 0))
                downloaded_bytes = 0
                
                with open(save_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 128):
                        if cancel_token and cancel_token.is_cancelled:
                            logger.info("Direct HTTP download cancelled by user.")
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
                                logger.error(f"Callback error in download: {e}")
                                
        logger.info(f"Download complete: {save_path}")
