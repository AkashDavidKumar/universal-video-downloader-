import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiosqlite
from loguru import logger

DEFAULT_DB_PATH = Path.home() / ".video_downloader_pro" / "database.db"
SCHEMA_FILE_PATH = Path(__file__).parent / "schema.sql"

class DatabaseManager:
    """Manages the local SQLite database for queue state, recent URLs, and metadata caching."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _connect(self):
        """Asynchronous context manager to yield a configured connection."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys=ON;")
            await db.execute("PRAGMA journal_mode=WAL;")
            db.row_factory = sqlite3.Row
            yield db

    async def initialize(self) -> None:
        """Initializes the database schema if tables do not exist."""
        logger.info(f"Initializing database at: {self.db_path}")
        
        if not SCHEMA_FILE_PATH.exists():
            logger.error(f"Database schema file not found at: {SCHEMA_FILE_PATH}")
            raise FileNotFoundError(f"Schema file missing: {SCHEMA_FILE_PATH}")
            
        with open(SCHEMA_FILE_PATH, "r", encoding="utf-8") as f:
            schema_script = f.read()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA foreign_keys=ON;")
            await db.executescript(schema_script)
            await db.commit()
            
        logger.info("Database schema initialized successfully.")

    async def add_download(
        self,
        url: str,
        title: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        duration: Optional[float] = None,
        status: str = "queued",
        save_path: Optional[str] = None,
        resolution: Optional[str] = None,
        codec: Optional[str] = None,
        container: Optional[str] = None,
        format_id: Optional[str] = None
    ) -> int:
        """Inserts a new download record. Returns the generated download ID."""
        query = """
            INSERT INTO downloads (
                url, title, thumbnail_url, duration, status, save_path, resolution, codec, container, format_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        async with self._connect() as db:
            async with db.execute(
                query, (url, title, thumbnail_url, duration, status, save_path, resolution, codec, container, format_id)
            ) as cursor:
                download_id = cursor.lastrowid
            await db.commit()
        logger.debug(f"Added download entry with ID: {download_id} for URL: {url}")
        return download_id

    async def update_download_status(self, download_id: int, status: str, error_message: Optional[str] = None) -> None:
        """Updates the status and optional error message of a download."""
        query = "UPDATE downloads SET status = ?, error_message = ? WHERE id = ?"
        async with self._connect() as db:
            await db.execute(query, (status, error_message, download_id))
            await db.commit()
        logger.debug(f"Updated download ID: {download_id} status to: {status}")

    async def update_download_progress(self, download_id: int, downloaded_bytes: int, total_bytes: int, progress: float) -> None:
        """Updates the downloaded bytes, total bytes, and progress percentage."""
        query = "UPDATE downloads SET downloaded_bytes = ?, total_bytes = ?, progress = ? WHERE id = ?"
        async with self._connect() as db:
            await db.execute(query, (downloaded_bytes, total_bytes, progress, download_id))
            await db.commit()

    async def get_download(self, download_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single download record by ID."""
        query = "SELECT * FROM downloads WHERE id = ?"
        async with self._connect() as db:
            async with db.execute(query, (download_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_download_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves a list of all download entries ordered by creation time (newest first)."""
        query = "SELECT * FROM downloads ORDER BY created_at DESC LIMIT ?"
        async with self._connect() as db:
            async with db.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def delete_download(self, download_id: int) -> None:
        """Deletes a download record by ID."""
        query = "DELETE FROM downloads WHERE id = ?"
        async with self._connect() as db:
            await db.execute(query, (download_id,))
            await db.commit()
        logger.debug(f"Deleted download record ID: {download_id}")

    async def add_metadata(
        self,
        download_id: int,
        description: Optional[str] = None,
        uploader: Optional[str] = None,
        upload_date: Optional[str] = None,
        source_url: Optional[str] = None,
        raw_json: Optional[Dict[str, Any]] = None
    ) -> None:
        """Saves metadata for a downloaded video."""
        raw_json_str = json.dumps(raw_json) if raw_json else None
        query = """
            INSERT OR REPLACE INTO metadata (
                download_id, description, uploader, upload_date, source_url, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        async with self._connect() as db:
            await db.execute(query, (download_id, description, uploader, upload_date, source_url, raw_json_str))
            await db.commit()
        logger.debug(f"Saved metadata for download ID: {download_id}")

    async def get_metadata(self, download_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves video metadata for a given download ID."""
        query = "SELECT * FROM metadata WHERE download_id = ?"
        async with self._connect() as db:
            async with db.execute(query, (download_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    res = dict(row)
                    if res.get("raw_json"):
                        res["raw_json"] = json.loads(res["raw_json"])
                    return res
                return None

    async def add_recent_url(self, url: str) -> None:
        """Caches a recently analyzed URL."""
        query = "INSERT OR REPLACE INTO recent_urls (url, visited_at) VALUES (?, (STRFTIME('%Y-%m-%d %H:%M:%f', 'now')))"
        async with self._connect() as db:
            await db.execute(query, (url,))
            await db.commit()

    async def get_recent_urls(self, limit: int = 15) -> List[str]:
        """Retrieves the list of recent URLs."""
        query = "SELECT url FROM recent_urls ORDER BY visited_at DESC LIMIT ?"
        async with self._connect() as db:
            async with db.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

    async def clear_history(self) -> None:
        """Deletes all entries from the downloads and recent_urls tables."""
        async with self._connect() as db:
            await db.execute("DELETE FROM downloads")
            await db.execute("DELETE FROM recent_urls")
            await db.commit()
        logger.info("Cleared all download history and cached URLs.")
