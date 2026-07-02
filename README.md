# Universal Video Downloader

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/GUI-PySide6-41cd52?logo=qt&logoColor=white)
![yt-dlp](https://img.shields.io/badge/backend-yt--dlp-red)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/Tests-13%20passing-brightgreen)
![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-blueviolet)

A feature-rich, open-source video downloader with a **native desktop GUI**, a full **CLI**, and a **React web frontend**. Built on a modular Python backend with an async download engine, plugin-based extractor system, and SQLite state management.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🎬 **Multi-site support** | YouTube, Vimeo, Instagram, Twitter, TikTok, and 1 000+ others via yt-dlp |
| 🖥 **Desktop GUI** | Native PySide6 app with dark/light themes, animated queue cards, format picker |
| ⌨ **Full CLI** | `analyze` and `download` commands for scripting and automation |
| ⚡ **Async Queue** | asyncio-powered concurrent downloads with pause, resume, and cancel |
| 🔌 **Plugin Extractors** | Drop-in extractor plugins — add a new site in one file |
| 🗄 **SQLite Persistence** | Local database stores download history and recent URLs |
| 🔒 **Safe Paths** | Path traversal protection, filename sanitisation, auto-incrementing suffixes |
| 📦 **Standalone Binary** | Bundle into a single `.exe` or binary with PyInstaller |
| 🌐 **React Web Frontend** | Static landing page with live demo, install guide, and feature showcase |

---

## 🏗 Architecture

```
universal-video-downloader/
│
├── main.py                      # Entry point — GUI launcher + CLI commands (typer)
│
├── app/
│   ├── config/
│   │   └── settings.py          # Pydantic settings model, JSON persistence
│   │
│   ├── core/
│   │   ├── logger.py            # Loguru setup
│   │   └── path_utils.py        # Filename templates, safe destination paths
│   │
│   ├── database/
│   │   ├── schema.sql           # SQLite schema (downloads, metadata, recent_urls)
│   │   └── db_manager.py        # Async aiosqlite manager
│   │
│   ├── download/
│   │   ├── downloader.py        # DownloadTask — async streaming writer
│   │   └── queue_manager.py     # Concurrent scheduler, pause/resume/cancel
│   │
│   ├── extractors/
│   │   ├── base_extractor.py    # Abstract base class for all extractors
│   │   ├── extractor_manager.py # Auto-discovery, URL routing
│   │   ├── youtube_extractor.py # YouTube / Shorts via yt-dlp
│   │   ├── generic_extractor.py # Generic HTTP / HTML scraping fallback
│   │   └── mock_extractor.py    # Offline test extractor
│   │
│   └── ui/
│       ├── async_bridge.py      # Thread-safe Qt ↔ asyncio bridge
│       ├── components.py        # DownloadQueueCard, SettingsPanel, ImageLoadWorker
│       ├── main_window.py       # MainWindow — full PySide6 desktop UI
│       └── styles.py            # QSS dark/light themes
│
├── web/                         # React + Vite static frontend
│   ├── src/
│   │   ├── main.jsx             # Full React app (demo, features, install guide)
│   │   └── styles.css           # Design system — tokens, animations, glassmorphism
│   └── index.html
│
├── tests/                       # pytest test suite
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_download_engine.py
│   ├── test_path_utils.py
│   ├── test_settings.py
│   ├── test_extractor_manager.py
│   ├── test_extractors.py
│   ├── test_queue_manager.py
│   └── test_cli.py
│
├── requirements.txt
├── deploy_guide.md
└── README.md
```

**Data flow (download)**
```
User pastes URL
    → ExtractorManager.get_extractor_for_url()
    → extractor.analyze(url)       # fetches metadata + stream URLs via yt-dlp / HTTP
    → QueueManager.add_download()  # persists to SQLite, schedules task
    → DownloadTask.start()         # streams bytes to disk, fires progress callbacks
    → AsyncBridge signals          # updates Qt UI on main thread
```

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- `ffmpeg` (optional, needed to merge separate video/audio streams)
- Node.js 18+ (only for the web frontend)

### Python Backend & Desktop GUI

```bash
# 1. Clone the repository
git clone https://github.com/AkashDavidKumar/universal-video-downloader-.git
cd universal-video-downloader-

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Web Frontend (optional)

```bash
cd web
npm install
npm run dev       # development server at http://localhost:5173
npm run build     # production build → web/dist/
```

---

## 🖥 Usage

### Desktop GUI

```bash
python main.py
```

1. Paste a video URL into the input field.
2. Click **Analyze** — metadata, thumbnail, and available formats load instantly.
3. Choose a format from the dropdown.
4. Click **Download Selected Format** — a progress card appears in the queue panel.
5. Pause, resume, or cancel any download at any time.

### CLI — Analyze a URL

```bash
python main.py analyze https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Output:
```
--- Media Metadata ---
Title:       Rick Astley — Never Gonna Give You Up
Uploader:    Rick Astley
Duration:    213.0 seconds
Thumbnail:   https://i.ytimg.com/vi/...

--- Available Formats ---
  - Format ID: yt_137       | Res: 1072x1920 | Ext: mp4  | Size: 31.72 MB
  - Format ID: yt_18        | Res: 358x640   | Ext: mp4  | Size: 6.59 MB
  - Format ID: yt_140       | Res: audio only| Ext: m4a  | Size: 1.44 MB
  ...
```

### CLI — Download a Video

```bash
# Download the best available format (first in list)
python main.py download https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Download a specific format
python main.py download https://www.youtube.com/watch?v=dQw4w9WgXcQ --format yt_18

# Save to a custom directory
python main.py download https://www.youtube.com/watch?v=dQw4w9WgXcQ --output ~/Videos
```

---

## 🔌 Writing a Custom Extractor

Create a new file in `app/extractors/` that subclasses `BaseExtractor`:

```python
# app/extractors/my_site_extractor.py
from .base_extractor import BaseExtractor

class MySiteExtractor(BaseExtractor):
    SUPPORTED_DOMAINS = ["mysite.com", "www.mysite.com"]

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return any(d in url for d in cls.SUPPORTED_DOMAINS)

    async def analyze(self, url: str) -> None:
        # fetch metadata and populate self._formats, self._title, etc.
        ...

    async def download(self, format_id, save_path, progress_callback=None, cancel_token=None):
        # stream bytes to save_path
        ...
```

The `ExtractorManager` auto-discovers all `BaseExtractor` subclasses in the `app/extractors/` directory — no registration needed.

---

## 🧪 Testing

```bash
# Run the full test suite
pytest -q

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_database.py -v
```

Current coverage: **17 tests across 8 modules**.

| Module | Tests |
|---|---|
| `test_database.py` | DB init, CRUD, cascade deletes |
| `test_download_engine.py` | Task lifecycle, progress callbacks |
| `test_path_utils.py` | Template rendering, traversal prevention |
| `test_settings.py` | Load, save, update settings |
| `test_extractor_manager.py` | Auto-discovery, URL routing |
| `test_extractors.py` | GenericExtractor analyze/download (mocked) |
| `test_queue_manager.py` | Concurrent downloads, cancel |
| `test_cli.py` | `analyze` and `download` CLI commands |

---

## ⚙ Configuration

Settings are stored in `~/.video_downloader_pro/settings.json` and can be changed via the **Settings** tab in the GUI.

| Setting | Default | Description |
|---|---|---|
| `download_dir` | `~/Downloads/VideoDownloaderPro` | Output folder |
| `filename_template` | `{title} - {resolution}` | Filename format |
| `concurrent_downloads` | `3` | Max parallel downloads |
| `chunk_size` | `1 048 576` (1 MB) | HTTP streaming chunk size |
| `retry_count` | `3` | Automatic retry on failure |
| `theme` | `dark` | `dark` / `light` / `system` |
| `proxy` | `null` | HTTP/HTTPS proxy URL |
| `ffmpeg_location` | `null` | Path to ffmpeg binary |

---

## 🌐 Deployment

See [deploy_guide.md](deploy_guide.md) for step-by-step instructions on hosting:
- **React frontend** → Vercel, Netlify, or GitHub Pages (free)
- **Python CLI** → Render or Railway (free tier)

> **Note:** The PySide6 desktop GUI cannot run on any cloud server — it requires a display.

---

## 🤝 Contributing

Contributions are welcome! Here's how:

1. **Fork** the repo and create a feature branch: `git checkout -b feat/my-extractor`
2. **Make changes** — follow the existing code style.
3. **Add tests** — new extractors should have at least basic unit tests.
4. **Run the test suite:** `pytest -q`
5. **Open a Pull Request** — describe what you changed and why.

Please open an **issue** before starting large changes so we can align on the approach.

---

## 📜 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — the powerful download engine powering the YouTube extractor
- [PySide6](https://doc.qt.io/qtforpython-6/) — cross-platform native desktop GUI
- [httpx](https://www.python-httpx.org/) — async HTTP client for streaming downloads
- [aiosqlite](https://github.com/omnilib/aiosqlite) — async SQLite interface
- [Loguru](https://github.com/Delgan/loguru) — beautiful Python logging
- [Typer](https://typer.tiangolo.com/) — CLI framework
- [Vite](https://vitejs.dev/) + [React](https://react.dev/) — web frontend
