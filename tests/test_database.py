import pytest
from app.database.db_manager import DatabaseManager

pytestmark = pytest.mark.asyncio

async def test_downloads_table_crud(test_db):
    """Tests insert, update, retrieval, and deletion of download items."""
    # 1. Add download
    d_id = await test_db.add_download(
        url="https://example.com/video.mp4",
        title="Test Video Title",
        status="queued",
        resolution="720p",
        container="mp4"
    )
    assert d_id == 1

    # 2. Retrieve download
    record = await test_db.get_download(d_id)
    assert record is not None
    assert record["title"] == "Test Video Title"
    assert record["status"] == "queued"

    # 3. Update Progress & Status
    await test_db.update_download_progress(d_id, 500, 1000, 50.0)
    await test_db.update_download_status(d_id, "downloading")
    
    updated_rec = await test_db.get_download(d_id)
    assert updated_rec["progress"] == 50.0
    assert updated_rec["status"] == "downloading"

    # 4. Get History
    history = await test_db.get_download_history(limit=5)
    assert len(history) == 1
    assert history[0]["id"] == d_id

    # 5. Delete record
    await test_db.delete_download(d_id)
    deleted_rec = await test_db.get_download(d_id)
    assert deleted_rec is None

async def test_metadata_cascade(test_db):
    """Verifies metadata is cascadingly deleted if parent download item is deleted."""
    d_id = await test_db.add_download(url="https://example.com/video.mp4", status="queued")
    
    await test_db.add_metadata(
        download_id=d_id,
        description="Detailed description.",
        uploader="Antigravity",
        raw_json={"uploader": "Antigravity", "tags": ["python"]}
    )

    # Verify metadata exists
    meta = await test_db.get_metadata(d_id)
    assert meta is not None
    assert meta["uploader"] == "Antigravity"
    assert meta["raw_json"]["tags"] == ["python"]

    # Delete download and check metadata cascade
    await test_db.delete_download(d_id)
    meta_deleted = await test_db.get_metadata(d_id)
    assert meta_deleted is None

async def test_recent_urls(test_db):
    """Tests recent URL cache inserts and limit retrieval."""
    urls = [
        "https://example.com/v1",
        "https://example.com/v2",
        "https://example.com/v3"
    ]
    for url in urls:
        await test_db.add_recent_url(url)

    recent = await test_db.get_recent_urls(limit=2)
    assert len(recent) == 2
    # Newest is first
    assert recent[0] == "https://example.com/v3"
    assert recent[1] == "https://example.com/v2"
