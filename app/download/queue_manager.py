import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from loguru import logger
from .downloader import DownloadTask
from ..database.db_manager import DatabaseManager

class QueueManager:
    """Manages the download queue, active downloads, concurrency, and DB status updates."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        max_concurrent: int = 3,
        speed_limit: int = 0,
        chunk_size: int = 1024 * 1024,
        retry_count: int = 3
    ):
        self.db_manager = db_manager
        self.max_concurrent = max_concurrent
        self.speed_limit = speed_limit
        self.chunk_size = chunk_size
        self.retry_count = retry_count

        self.tasks: Dict[int, DownloadTask] = {}  # download_id -> DownloadTask
        self.active_futures: Dict[int, asyncio.Task] = {}  # download_id -> running asyncio Task
        
        self._schedule_event = asyncio.Event()
        self._loop_task: Optional[asyncio.Task] = None
        self._stopped = False
        
        # Callback to notify the GUI/CLI of updates
        self.on_progress_update: Optional[Callable[[int, Dict[str, Any]], None]] = None

    def start(self) -> None:
        """Starts the background queue scheduling loop."""
        self._stopped = False
        self._loop_task = asyncio.create_task(self._scheduler_loop())
        logger.info("QueueManager scheduler started.")

    async def stop(self) -> None:
        """Stops the scheduler and pauses/cancels all running downloads."""
        self._stopped = True
        self._schedule_event.set()
        
        # Stop background scheduler
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        # Pause running tasks
        running_ids = list(self.active_futures.keys())
        for task_id in running_ids:
            task = self.tasks.get(task_id)
            if task and task.status == "downloading":
                task.pause()
                await self.db_manager.update_download_status(task_id, "paused")

        # Wait for futures to complete
        if self.active_futures:
            await asyncio.gather(*self.active_futures.values(), return_exceptions=True)
            self.active_futures.clear()

        logger.info("QueueManager scheduler stopped.")

    async def add_download(
        self,
        url: str,
        title: str,
        save_path: str,
        format_id: str = "default",
        thumbnail_url: Optional[str] = None,
        duration: Optional[float] = None,
        resolution: Optional[str] = None,
        codec: Optional[str] = None,
        container: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> int:
        """Adds a download to the database and queues it in the scheduler."""
        # 1. Store in Database as 'queued'
        download_id = await self.db_manager.add_download(
            url=url,
            title=title,
            thumbnail_url=thumbnail_url,
            duration=duration,
            status="queued",
            save_path=save_path,
            resolution=resolution,
            codec=codec,
            container=container,
            format_id=format_id
        )

        # 2. Instantiate DownloadTask
        task = DownloadTask(
            download_id=download_id,
            url=url,
            save_path=save_path,
            format_id=format_id,
            headers=headers,
            speed_limit=self.speed_limit,
            chunk_size=self.chunk_size,
            retry_count=self.retry_count,
            progress_callback=self._task_progress_callback
        )
        self.tasks[download_id] = task
        
        logger.info(f"Queued download ID {download_id}: '{title}'")
        
        # Trigger scheduler
        self._schedule_event.set()
        return download_id

    async def pause_download(self, download_id: int) -> None:
        """Pauses a download task."""
        task = self.tasks.get(download_id)
        if task:
            task.pause()
            await self.db_manager.update_download_status(download_id, "paused")
            self._schedule_event.set()

    async def resume_download(self, download_id: int) -> None:
        """Resumes a paused download task."""
        task = self.tasks.get(download_id)
        if task and task.status == "paused":
            task.resume()
            await self.db_manager.update_download_status(download_id, "queued")
            self._schedule_event.set()

    async def cancel_download(self, download_id: int) -> None:
        """Cancels a download task and deletes the temporary file."""
        task = self.tasks.get(download_id)
        if task:
            task.cancel()
            await self.db_manager.update_download_status(download_id, "cancelled")
            
            # Remove from scheduler structures
            if download_id in self.active_futures:
                self.active_futures[download_id].cancel()
                
            # Delete incomplete file
            if task.save_path.exists():
                try:
                    task.save_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete cancelled file {task.save_path}: {e}")
                    
            self._schedule_event.set()

    async def retry_download(self, download_id: int) -> None:
        """Resets a failed download task and queues it for retry."""
        db_task = await self.db_manager.get_download(download_id)
        if not db_task:
            return

        # Delete any partially downloaded file to clean up before retry
        save_path = Path(db_task["save_path"])
        if save_path.exists():
            try:
                save_path.unlink()
            except Exception:
                pass

        # Create new task instance
        task = DownloadTask(
            download_id=download_id,
            url=db_task["url"],
            save_path=db_task["save_path"],
            format_id=db_task.get("format_id") or "default",
            speed_limit=self.speed_limit,
            chunk_size=self.chunk_size,
            retry_count=self.retry_count,
            progress_callback=self._task_progress_callback
        )
        self.tasks[download_id] = task
        
        await self.db_manager.update_download_status(download_id, "queued")
        logger.info(f"Re-queued download ID {download_id} for retry.")
        
        self._schedule_event.set()

    def _task_progress_callback(self, download_id: int, metrics: Dict[str, Any]) -> None:
        """Receives progress updates from active DownloadTasks and propagates them."""
        # 1. Update database periodically
        # Note: In a production environment, you might throttle progress DB updates to avoid high lock overhead.
        # We can update DB asynchronously without blocking
        asyncio.create_task(
            self.db_manager.update_download_progress(
                download_id,
                metrics["downloaded_bytes"],
                metrics["total_bytes"],
                metrics["progress"]
            )
        )
        
        # 2. Invoke UI/CLI callback
        if self.on_progress_update:
            try:
                self.on_progress_update(download_id, metrics)
            except Exception as e:
                logger.error(f"UI update callback failed: {e}")

    async def _scheduler_loop(self) -> None:
        """Background scheduling loop that handles starting queued tasks."""
        while not self._stopped:
            # 1. Clean up completed/failed futures
            finished_ids = []
            for download_id, fut in self.active_futures.items():
                if fut.done():
                    finished_ids.append(download_id)
                    # Check if exceptions occurred during execution
                    exc = fut.exception()
                    task = self.tasks.get(download_id)
                    if exc:
                        logger.error(f"Task ID {download_id} encountered exception: {exc}")
                        asyncio.create_task(self.db_manager.update_download_status(download_id, "failed", str(exc)))
                    elif task:
                        if task.status == "completed":
                            asyncio.create_task(self.db_manager.update_download_status(download_id, "completed"))
                        elif task.status == "cancelled":
                            asyncio.create_task(self.db_manager.update_download_status(download_id, "cancelled"))
                        elif task.status == "paused":
                            asyncio.create_task(self.db_manager.update_download_status(download_id, "paused"))

            for download_id in finished_ids:
                self.active_futures.pop(download_id, None)

            # 2. Count active downloading tasks
            active_count = len(self.active_futures)

            # 3. Schedule next queued tasks up to max_concurrent limit
            if active_count < self.max_concurrent:
                queued_tasks = [t for t in self.tasks.values() if t.status == "queued"]
                
                for task in queued_tasks:
                    if len(self.active_futures) >= self.max_concurrent:
                        break
                        
                    logger.info(f"Starting scheduled download ID {task.download_id} ({task.save_path.name})")
                    task.status = "downloading"
                    asyncio.create_task(self.db_manager.update_download_status(task.download_id, "downloading"))
                    
                    # Start the task
                    fut = asyncio.create_task(task.start())
                    self.active_futures[task.download_id] = fut

            # 4. Wait for next schedule trigger (or 1 second timeout for state sync)
            try:
                await asyncio.wait_for(self._schedule_event.wait(), timeout=1.0)
                self._schedule_event.clear()
            except asyncio.TimeoutError:
                pass
