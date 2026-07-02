import asyncio
import threading
from typing import Coroutine, Optional, Dict, Any
from PySide6.QtCore import QObject, Signal
from loguru import logger

from ..config.settings import SettingsManager
from ..database.db_manager import DatabaseManager
from ..extractors.extractor_manager import ExtractorManager
from ..download.queue_manager import QueueManager

class AsyncSignalBridge(QObject):
    """Thread-safe bridge that routes async engine events to PySide6 Qt slots."""
    
    # Analysis Signals
    analysis_started = Signal()
    analysis_completed = Signal(dict)  # Emits metadata dict
    analysis_failed = Signal(str)      # Emits error message

    # Download Signals
    download_progress = Signal(int, dict)       # download_id, metrics_dict
    download_status_changed = Signal(int, str, str) # download_id, new_status, error_msg

    def __init__(self):
        super().__init__()

class AsyncEngineManager:
    """Manages the background asyncio event loop thread and instantiates core logic managers."""

    def __init__(self, settings_mgr: SettingsManager):
        self.settings_mgr = settings_mgr
        self.bridge = AsyncSignalBridge()
        
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        
        # Async managers (initialized inside the loop)
        self.db_mgr: Optional[DatabaseManager] = None
        self.extractor_mgr: Optional[ExtractorManager] = None
        self.queue_mgr: Optional[QueueManager] = None

    def start(self) -> None:
        """Starts the background event loop thread."""
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, args=(self.loop,), daemon=True)
        self.thread.start()
        
        # Initialize async managers in the loop
        future = asyncio.run_coroutine_threadsafe(self._setup_managers(), self.loop)
        future.result()  # Block until setup is complete to ensure managers are active
        
        logger.info("Background asyncio loop thread started successfully.")

    def stop(self) -> None:
        """Gracefully shuts down running downloads and stops the loop thread."""
        if self.loop and self.loop.is_running():
            # Stop QueueManager first
            if self.queue_mgr:
                fut = asyncio.run_coroutine_threadsafe(self.queue_mgr.stop(), self.loop)
                fut.result()

            self.loop.call_soon_threadsafe(self.loop.stop())
            self.thread.join(timeout=3.0)
            logger.info("Background asyncio loop thread shut down.")

    def run_coroutine(self, coro: Coroutine) -> Any:
        """Submits a coroutine to run on the background event loop.
        
        Returns:
            A concurrent.futures.Future object to track results.
        """
        if not self.loop:
            raise RuntimeError("Event loop is not running. Call start() first.")
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def _run_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Target for the background thread."""
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        finally:
            loop.close()
            logger.debug("Background event loop closed.")

    async def _setup_managers(self) -> None:
        """Instantiates and initializes the database and queue managers inside the async loop."""
        # 1. Database
        self.db_mgr = DatabaseManager()
        await self.db_mgr.initialize()

        # 2. Extractor Plugin Manager
        self.extractor_mgr = ExtractorManager()
        self.extractor_mgr.load_all()

        # 3. Queue Manager
        self.queue_mgr = QueueManager(
            db_manager=self.db_mgr,
            max_concurrent=self.settings_mgr.settings.concurrent_downloads,
            speed_limit=self.settings_mgr.settings.proxy,  # proxy or limit
            chunk_size=self.settings_mgr.settings.chunk_size,
            retry_count=self.settings_mgr.settings.retry_count
        )
        # Bind the queue progress update back to our Qt Bridge signal emission
        self.queue_mgr.on_progress_update = self._on_task_progress
        self.queue_mgr.start()

    def _on_task_progress(self, download_id: int, metrics: Dict[str, Any]) -> None:
        """Triggered from QueueManager, forwards progress to PySide6 UI thread."""
        self.bridge.download_progress.emit(download_id, metrics)
        
        # If status changes, emit status signal
        if "status" in metrics:
            self.bridge.download_status_changed.emit(
                download_id,
                metrics["status"],
                metrics.get("error", "")
            )

    async def analyze_url_task(self, url: str) -> None:
        """Coroutine to analyze a video page URL and emit metadata back to Qt GUI."""
        self.bridge.analysis_started.emit()
        try:
            # 1. Get correct extractor
            extractor = self.extractor_mgr.get_extractor_for_url(url)
            
            # 2. Add URL to recent URL cache
            await self.db_mgr.add_recent_url(url)

            # 3. Analyze page
            await extractor.analyze(url)

            # 4. Compile metadata payload
            metadata = {
                "url": url,
                "title": extractor.get_title(),
                "thumbnail": extractor.get_thumbnail(),
                "duration": extractor.get_duration(),
                "uploader": extractor.get_uploader(),
                "description": extractor.get_description(),
                "formats": extractor.get_available_formats(),
                "extractor_name": extractor.__class__.__name__
            }
            logger.info(f"Analysis completed for URL: {url}")
            self.bridge.analysis_completed.emit(metadata)
            
        except Exception as e:
            logger.error(f"Analysis failed for URL {url}: {e}")
            self.bridge.analysis_failed.emit(str(e))
