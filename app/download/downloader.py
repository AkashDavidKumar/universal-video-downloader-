import asyncio
import time
from pathlib import Path
from typing import Callable, Optional, Dict, Any
import httpx
from loguru import logger

class CancelToken:
    """Token to signal cancellation across asynchronous boundaries."""
    def __init__(self):
        self._is_cancelled = False

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def cancel(self) -> None:
        self._is_cancelled = True

class DownloadTask:
    """Represents a single active or queued download job."""

    def __init__(
        self,
        download_id: int,
        url: str,
        save_path: str,
        format_id: str = "default",
        headers: Optional[Dict[str, str]] = None,
        speed_limit: int = 0,      # In bytes per second. 0 means unlimited.
        chunk_size: int = 1024 * 1024, # Default 1MB chunks
        retry_count: int = 3,
        progress_callback: Optional[Callable[[int, Dict[str, Any]], None]] = None
    ):
        self.download_id = download_id
        self.url = url
        self.save_path = Path(save_path)
        self.format_id = format_id
        self.headers = headers or {}
        self.speed_limit = speed_limit
        self.chunk_size = chunk_size
        self.retry_count = retry_count
        self.progress_callback = progress_callback

        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.status = "queued"  # queued, downloading, paused, completed, failed, cancelled
        self.error_message = ""
        
        self.cancel_token = CancelToken()
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # True means not paused

        self._start_time = 0.0
        self._elapsed_time = 0.0
        self._speed = 0.0
        self._retries_left = retry_count

    def pause(self) -> None:
        """Pauses the download task."""
        if self.status == "downloading":
            self.pause_event.clear()
            self.status = "paused"
            logger.info(f"Download ID {self.download_id} paused by user.")

    def resume(self) -> None:
        """Resumes the download task."""
        if self.status == "paused":
            self.pause_event.set()
            self.status = "downloading"
            logger.info(f"Download ID {self.download_id} resumed by user.")

    def cancel(self) -> None:
        """Cancels the download task."""
        self.cancel_token.cancel()
        self.pause_event.set()  # Break out of any wait loops
        self.status = "cancelled"
        logger.info(f"Download ID {self.download_id} cancelled by user.")

    async def start(self) -> None:
        """Starts the download task using the matching extractor's download implementation."""
        self.status = "downloading"
        self._start_time = time.time()
        
        try:
            if self.cancel_token.is_cancelled:
                self.status = "cancelled"
                return

            if not self.pause_event.is_set():
                self.status = "paused"
                return

            # Dynamically resolve extractor to support plugin downloads
            from ..extractors.extractor_manager import ExtractorManager
            extractor_mgr = ExtractorManager()
            extractor_mgr.load_all()
            
            extractor = extractor_mgr.get_extractor_for_url(self.url)
            
            # Map progress callback
            def local_callback(metrics):
                if self.progress_callback:
                    self.progress_callback(self.download_id, metrics)
                    
            # Delegate download to extractor
            await extractor.analyze(self.url)
            await extractor.download(
                format_id=self.format_id,
                save_path=str(self.save_path),
                progress_callback=local_callback,
                cancel_token=self.cancel_token
            )
            
            # Check status after execution completes
            if self.cancel_token.is_cancelled:
                self.status = "cancelled"
            elif not self.pause_event.is_set():
                self.status = "paused"
            else:
                self.status = "completed"
                logger.info(f"Download ID {self.download_id} finished successfully.")
                
        except Exception as e:
            if self.cancel_token.is_cancelled:
                self.status = "cancelled"
            elif not self.pause_event.is_set():
                self.status = "paused"
            else:
                self.status = "failed"
                self.error_message = str(e)
                logger.error(f"Download ID {self.download_id} failed: {e}")
                raise e
