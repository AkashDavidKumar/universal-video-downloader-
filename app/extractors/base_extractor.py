from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseExtractor(ABC):
    """Abstract base class that all extractor plugins must implement."""

    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """Checks if this extractor can handle the provided URL.
        
        Args:
            url: The media page URL.
            
        Returns:
            True if supported, False otherwise.
        """
        pass

    @abstractmethod
    async def analyze(self, url: str) -> None:
        """Fetches the page, parses the HTML/JSON, and extracts streams and metadata.
        
        Args:
            url: The media page URL.
            
        Raises:
            Exception: If connection fails or parsing error occurs.
        """
        pass

    @abstractmethod
    def get_title(self) -> str:
        """Returns the media title."""
        pass

    @abstractmethod
    def get_thumbnail(self) -> str:
        """Returns the URL of the thumbnail image."""
        pass

    @abstractmethod
    def get_duration(self) -> float:
        """Returns the media duration in seconds. Returns 0.0 if live or unknown."""
        pass

    @abstractmethod
    def get_uploader(self) -> str:
        """Returns the uploader or author name. Returns 'Unknown' if not available."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Returns the description of the media. Returns empty string if not available."""
        pass

    @abstractmethod
    def get_available_formats(self) -> List[Dict[str, Any]]:
        """Returns a list of available media streams.
        
        Format schema:
        {
            "format_id": str,          # Unique identifier for the format
            "url": str,                # Direct media stream URL
            "resolution": str,         # e.g., '1080p', '720p', 'audio'
            "ext": str,                # File extension (e.g. 'mp4', 'webm', 'mp3')
            "vcodec": str,             # Video codec (e.g., 'h264', 'vp9', 'none')
            "acodec": str,             # Audio codec (e.g., 'aac', 'opus', 'none')
            "vbitrate": Optional[int], # Video bitrate in kbps
            "abitrate": Optional[int], # Audio bitrate in kbps
            "fps": Optional[int],      # Frames per second
            "filesize": Optional[int], # Stream file size in bytes (if known)
            "headers": Optional[dict], # Special HTTP headers required to retrieve stream
            "is_dash": bool,           # If stream needs merging (separate video & audio)
            "is_audio_only": bool,
            "is_video_only": bool
        }
        """
        pass

    @abstractmethod
    async def download(
        self,
        format_id: str,
        save_path: str,
        progress_callback: Optional[Any] = None,
        cancel_token: Optional[Any] = None
    ) -> None:
        """Downloads the selected format.
        
        Args:
            format_id: The ID of the format to download.
            save_path: The filesystem path to save the file.
            progress_callback: Optional callback receiving progress dicts.
            cancel_token: Optional token to signal cancellation.
        """
        pass
