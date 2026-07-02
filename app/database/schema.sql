CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT,
    thumbnail_url TEXT,
    duration REAL,
    status TEXT NOT NULL CHECK(status IN ('queued', 'downloading', 'paused', 'completed', 'failed', 'cancelled')),
    progress REAL DEFAULT 0.0,
    downloaded_bytes INTEGER DEFAULT 0,
    total_bytes INTEGER DEFAULT 0,
    save_path TEXT,
    resolution TEXT,
    codec TEXT,
    container TEXT,
    error_message TEXT,
    format_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metadata (
    download_id INTEGER PRIMARY KEY,
    description TEXT,
    uploader TEXT,
    upload_date TEXT,
    source_url TEXT,
    download_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_json TEXT,
    FOREIGN KEY(download_id) REFERENCES downloads(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recent_urls (
    url TEXT PRIMARY KEY,
    visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS update_downloads_timestamp 
AFTER UPDATE ON downloads
BEGIN
    UPDATE downloads SET updated_at = CURRENT_TIMESTAMP WHERE id = new.id;
END;
