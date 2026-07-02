# Universal Video Downloader

Universal Video Downloader is a Python-based media downloader with a desktop GUI, a CLI workflow, and a lightweight web frontend shell. It focuses on modular extraction, queue-based downloads, and a clean developer experience for local use and simple deployment.

## What this project does

- Analyzes video URLs from supported sources.
- Extracts metadata such as title, uploader, duration, and available formats.
- Queues downloads with pause, resume, and cancel support.
- Stores download state and recent URLs in SQLite.
- Provides a simple web landing page for deployment and presentation.

## Features

- Python async downloader engine
- PySide6 desktop UI
- CLI commands for analysis and downloads
- Plugin-based extractor architecture
- SQLite-backed state management
- Minimal web frontend for hosting

## Project structure

- app/: application logic
  - config/: settings and configuration
  - core/: logger and path helpers
  - database/: SQLite schema and manager
  - download/: queue and downloader logic
  - extractors/: extractor implementations
  - ui/: desktop interface
- web/: static frontend entry point for hosting
- tests/: pytest coverage for database and download engine

## Installation

1. Clone the repository.
2. Create a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run locally

### Desktop UI

```bash
python main.py
```

### CLI analysis

```bash
python main.py analyze https://example.com/video
```

### CLI download

```bash
python main.py download https://example.com/video --output ./downloads
```

## Testing

Run the test suite with:

```bash
pytest -q
```

## Deployment notes

A deployment guide is available in [deploy_guide.md](deploy_guide.md). For free-tier hosting, keep the app lightweight and rely on SQLite for local persistence.

## Notes

The project currently uses a desktop-first interface, but the web folder provides a minimal React-style shell that can be served on Vercel or similar platforms. This keeps the project deployable while preserving the Python backend for the actual download workflow.
