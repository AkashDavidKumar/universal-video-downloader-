import asyncio
import pytest
from pathlib import Path
from app.download.downloader import DownloadTask, CancelToken
from app.download.queue_manager import QueueManager
from app.extractors.mock_extractor import MockExtractor

pytestmark = pytest.mark.asyncio

async def test_mock_download_execution(temp_dir):
    """Verifies that download execution works and invokes progress callbacks."""
    save_path = temp_dir / "mock_download.mp4"
    extractor = MockExtractor()
    await extractor.analyze("https://mockvideo.com/watch/1")
    
    callbacks = []
    def callback(metrics):
        callbacks.append(metrics)

    # Trigger mock download
    await extractor.download(
        format_id="1080p_mp4",
        save_path=str(save_path),
        progress_callback=callback
    )

    assert save_path.exists()
    assert len(callbacks) > 0
    assert callbacks[-1]["progress"] == 100.0
    assert callbacks[-1]["status"] == "downloading"  # Mock finishes write loop

async def test_download_cancellation(temp_dir):
    """Verifies that canceling a download task immediately interrupts execution."""
    save_path = temp_dir / "cancelled_download.mp4"
    extractor = MockExtractor()
    await extractor.analyze("https://mockvideo.com/watch/1")
    
    cancel_token = CancelToken()
    
    async def cancel_after_delay():
        await asyncio.sleep(0.1)
        cancel_token.cancel()

    # Launch download and cancellation tasks concurrently
    download_coro = extractor.download(
        format_id="1080p_mp4",
        save_path=str(save_path),
        cancel_token=cancel_token
    )
    
    with pytest.raises(asyncio.CancelledError):
        await asyncio.gather(download_coro, cancel_after_delay())

async def test_queue_manager_concurrency(test_db, temp_dir):
    """Verifies that the QueueManager respects max concurrent limits."""
    queue_mgr = QueueManager(
        db_manager=test_db,
        max_concurrent=2,
        chunk_size=1024 * 10,
        retry_count=1
    )
    queue_mgr.start()

    # Add 4 concurrent mock downloads
    task_ids = []
    for i in range(4):
        d_id = await queue_mgr.add_download(
            url=f"https://mockvideo.com/watch/{i}",
            title=f"Mock Video {i}",
            save_path=str(temp_dir / f"queue_video_{i}.mp4")
        )
        task_ids.append(d_id)

    # Let the scheduler loop start downloads
    await asyncio.sleep(0.5)

    # Verify concurrency constraint: only 2 should be active/downloading
    downloading_count = len(queue_mgr.active_futures)
    assert downloading_count <= 2

    # Clean up and stop
    await queue_mgr.stop()
