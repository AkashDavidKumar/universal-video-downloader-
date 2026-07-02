"""
Tests for QueueManager — add, complete lifecycle, concurrent limit, and cancel.
Uses MockExtractor so no real network requests are made.
"""
import sys
import asyncio
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.download.queue_manager import QueueManager
from app.database.db_manager import DatabaseManager

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def db(tmp_path):
    db_file = tmp_path / "queue_test.db"
    mgr = DatabaseManager(db_path=db_file)
    await mgr.initialize()
    return mgr


@pytest.fixture
async def queue(db, tmp_path):
    """Returns a started QueueManager with 1 slot and no speed limit."""
    qm = QueueManager(
        db_manager=db,
        max_concurrent=1,
        speed_limit=0,
        chunk_size=1024 * 128,
        retry_count=0,
    )
    qm.start()
    yield qm
    await qm.stop()


class TestQueueManagerLifecycle:
    async def test_add_download_returns_id(self, queue, tmp_path):
        """add_download() should return a positive integer download ID."""
        d_id = await queue.add_download(
            url="https://mockvideo.com/watch/1",
            title="Test Video",
            save_path=str(tmp_path / "out.mp4"),
            format_id="1080p_mp4",
        )
        assert isinstance(d_id, int)
        assert d_id > 0

    async def test_task_appears_in_tasks_dict(self, queue, tmp_path):
        """After adding, a task entry should be visible in queue.tasks."""
        d_id = await queue.add_download(
            url="https://mockvideo.com/watch/2",
            title="Test Video 2",
            save_path=str(tmp_path / "out2.mp4"),
            format_id="720p_mp4",
        )
        assert d_id in queue.tasks

    async def test_completed_download_status(self, queue, tmp_path):
        """A mock download should reach 'completed' within a reasonable timeout."""
        save = str(tmp_path / "complete_test.mp4")
        d_id = await queue.add_download(
            url="https://mockvideo.com/watch/3",
            title="Complete Test",
            save_path=save,
            format_id="audio_only",
        )

        # Poll until done or timeout
        deadline = asyncio.get_event_loop().time() + 60
        while asyncio.get_event_loop().time() < deadline:
            task = queue.tasks.get(d_id)
            if task and task.status in ("completed", "failed", "cancelled"):
                break
            await asyncio.sleep(0.5)

        task = queue.tasks.get(d_id)
        assert task is not None
        assert task.status == "completed", f"Expected completed, got {task.status}"

    async def test_cancel_mid_download(self, queue, tmp_path):
        """Cancelling a queued or downloading task should set status to 'cancelled'."""
        save = str(tmp_path / "cancel_test.mp4")
        d_id = await queue.add_download(
            url="https://mockvideo.com/watch/4",
            title="Cancel Test",
            save_path=save,
            format_id="1080p_mp4",  # Large file = slower = easier to cancel
        )

        # Give it a moment to start
        await asyncio.sleep(0.3)
        await queue.cancel_download(d_id)

        # Poll briefly for cancellation to propagate
        for _ in range(20):
            task = queue.tasks.get(d_id)
            if task and task.status in ("cancelled", "failed"):
                break
            await asyncio.sleep(0.2)

        task = queue.tasks.get(d_id)
        assert task is not None
        assert task.status in ("cancelled", "failed")

    async def test_progress_callback_fires(self, queue, tmp_path):
        """on_progress_update should be called at least once during download."""
        updates = []

        def on_progress(download_id, metrics):
            updates.append((download_id, metrics))

        queue.on_progress_update = on_progress

        save = str(tmp_path / "progress_test.mp4")
        d_id = await queue.add_download(
            url="https://mockvideo.com/watch/5",
            title="Progress Test",
            save_path=save,
            format_id="audio_only",
        )

        # Wait for completion
        deadline = asyncio.get_event_loop().time() + 60
        while asyncio.get_event_loop().time() < deadline:
            task = queue.tasks.get(d_id)
            if task and task.status in ("completed", "failed"):
                break
            await asyncio.sleep(0.5)

        assert len(updates) > 0, "No progress callbacks were fired"
        ids = [u[0] for u in updates]
        assert d_id in ids


class TestQueueManagerConcurrency:
    async def test_max_concurrent_respected(self, db, tmp_path):
        """With max_concurrent=1, only one download should run at a time."""
        qm = QueueManager(
            db_manager=db,
            max_concurrent=1,
            speed_limit=0,
            chunk_size=1024 * 128,
            retry_count=0,
        )
        qm.start()

        # Queue 3 downloads
        ids = []
        for i in range(3):
            d_id = await qm.add_download(
                url="https://mockvideo.com/watch/cc",
                title=f"Concurrent Video {i}",
                save_path=str(tmp_path / f"cc_{i}.mp4"),
                format_id="audio_only",
            )
            ids.append(d_id)

        # Check immediately — at most 1 should be actively downloading
        await asyncio.sleep(0.5)
        downloading = [
            t for t in qm.tasks.values() if t.status == "downloading"
        ]
        assert len(downloading) <= 1, f"More than 1 task running: {len(downloading)}"

        await qm.stop()
