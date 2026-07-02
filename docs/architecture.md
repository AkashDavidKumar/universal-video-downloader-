# System Architecture — Video Downloader Pro

This document describes the architectural layout, threading boundaries, and data flow patterns of **Video Downloader Pro**.

---

## 1. Clean Architecture Layers

The application is structured according to Clean Architecture to separate domain rules, database logic, and visual components.

```text
       +---------------------------------------------+
       |                  UI Layer                   |
       |  (main_window.py, components.py, styles.py) |
       +----------------------+----------------------+
                              | uses
                              v
       +----------------------+----------------------+
       |                 Domain Layer                |
       |  (settings.py, base_extractor.py)           |
       +----------------------+----------------------+
                              | implements / uses
                              v
       +----------------------+----------------------+
       |                 Engine Layer                |
       |  (downloader.py, queue_manager.py, db)      |
       +---------------------------------------------+
```

### Components:
1. **Core / Domain:** Contains configuration models, paths, logging, and common interfaces like `BaseExtractor`.
2. **Database:** SQLite schemas and async SQLite query scripts. Maintains historical and active queue state.
3. **Extractors & Plugins:** Discovery loaders and site-specific scrapers.
4. **Download Engine:** HTTP chunk streaming, speed limits, range resumes, and FFmpeg merging.
5. **UI Layer:** PySide6 layouts and styling.

---

## 2. Threading & Event Loops

To guarantee that heavy network IO, database queries, and subprocess calls do not freeze the desktop application, the application runs on **two separate threads**:

1. **Main UI Thread (Qt Event Loop):** Responsible for rendering views, capturing clipboard data, and updating widget progress.
2. **Asyncio Engine Thread (Python Event Loop):** Dedicated background thread running a daemon asyncio loop. All network calls (`httpx`), database transactions (`aiosqlite`), and merges (`ffmpeg`) execute strictly inside this loop.

### Communication:
- **UI -> Engine:** UI submits tasks to the loop thread via `asyncio.run_coroutine_threadsafe(coro, loop)`.
- **Engine -> UI:** The engine broadcasts status and progress updates back to the UI thread using thread-safe PySide6 **Qt Signals** (which internally queue messages on the main loop).

---

## 3. Database Schema

The database relies on three tables with constraints and automated triggers:
- `downloads`: Main table tracking media URL, titles, container formats, and current progress metrics.
- `metadata`: Sub-table mapping complete extracted payloads.
- `recent_urls`: LRU list of URL entries.

An automated SQLite trigger updates timestamps on modification:
```sql
CREATE TRIGGER IF NOT EXISTS update_downloads_timestamp 
AFTER UPDATE ON downloads
BEGIN
    UPDATE downloads SET updated_at = CURRENT_TIMESTAMP WHERE id = new.id;
END;
```
