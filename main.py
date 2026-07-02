"""
Video Downloader Pro - Main Application Entrypoint & CLI Suite.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional
import typer
from loguru import logger

# Add the parent directory of this file to sys.path to ensure absolute package imports resolve correctly
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import SettingsManager
from app.core.logger import setup_logger
from app.core.path_utils import render_filename_template, get_safe_destination_path
from app.database.db_manager import DatabaseManager
from app.extractors.extractor_manager import ExtractorManager
from app.download.queue_manager import QueueManager

cli_app = typer.Typer(help="Video Downloader Pro - CLI & GUI Interface")

def run_gui(settings_mgr: SettingsManager) -> None:
    """Launches the PySide6 graphical user interface."""
    from PySide6.QtWidgets import QApplication
    from app.ui.main_window import MainWindow
    from app.ui.async_bridge import AsyncEngineManager

    app = QApplication(sys.argv)
    app.setApplicationName("Video Downloader Pro")

    # Start the async engine manager (background thread and event loop)
    async_engine = AsyncEngineManager(settings_mgr)
    async_engine.start()

    window = MainWindow(settings_mgr, async_engine)
    window.show()

    # Run the Qt main event loop
    sys.exit(app.exec())

@cli_app.command()
def gui():
    """Launch the Video Downloader Pro Graphical User Interface (GUI)."""
    settings_mgr = SettingsManager()
    setup_logger("INFO")
    logger.info("Starting application in GUI mode...")
    run_gui(settings_mgr)

@cli_app.command()
def web(
    host: str = typer.Option("127.0.0.1", help="The host to bind to"),
    port: int = typer.Option(8000, help="The port to bind to")
):
    """Launch the web application (FastAPI + React)."""
    import uvicorn
    setup_logger("INFO")
    logger.info(f"Starting web server at http://{host}:{port}")
    uvicorn.run("app.api.server:app", host=host, port=port, log_level="info")

def safe_echo(text: str, fg=None, bold=False, err=False):
    encoding = sys.stdout.encoding or 'utf-8'
    safe_text = text.encode(encoding, errors='replace').decode(encoding)
    typer.secho(safe_text, fg=fg, bold=bold, err=err)

@cli_app.command()
def analyze(
    url: str = typer.Argument(..., help="The video page URL to analyze")
):
    """Analyze a webpage URL to extract video metadata and list formats."""
    settings_mgr = SettingsManager()
    setup_logger("INFO")
    
    async def _analyze():
        # Setup temporary managers for CLI analysis
        extractor_mgr = ExtractorManager()
        extractor_mgr.load_all()
        
        db_mgr = DatabaseManager()
        await db_mgr.initialize()
        await db_mgr.add_recent_url(url)

        try:
            safe_echo(f"Analyzing URL: {url}...")
            extractor = extractor_mgr.get_extractor_for_url(url)
            await extractor.analyze(url)
            
            safe_echo("\n--- Media Metadata ---", fg=typer.colors.CYAN, bold=True)
            safe_echo(f"Title:       {extractor.get_title()}")
            safe_echo(f"Uploader:    {extractor.get_uploader()}")
            safe_echo(f"Duration:    {extractor.get_duration()} seconds")
            safe_echo(f"Thumbnail:   {extractor.get_thumbnail()}")
            safe_echo(f"Description: {extractor.get_description()[:120]}...")
            
            safe_echo("\n--- Available Formats ---", fg=typer.colors.CYAN, bold=True)
            for fmt in extractor.get_available_formats():
                fid = fmt["format_id"]
                res = fmt.get("resolution") or "unknown"
                ext = fmt.get("ext") or "mp4"
                size = fmt.get("filesize") or 0
                size_str = f"{size / (1024*1024):.2f} MB" if size > 0 else "unknown size"
                safe_echo(f"  - Format ID: {fid:<15} | Res: {res:<10} | Ext: {ext:<5} | Size: {size_str}")
        except Exception as e:
            safe_echo(f"Analysis failed: {e}", fg=typer.colors.RED, err=True)

    asyncio.run(_analyze())

@cli_app.command()
def download(
    url: str = typer.Argument(..., help="The URL of the video to download"),
    format_id: Optional[str] = typer.Option(None, "--format", "-f", help="Specific Format ID to download"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Custom output folder path")
):
    """Download a video from the specified URL using the CLI."""
    settings_mgr = SettingsManager()
    setup_logger("INFO")
    
    # Override settings target folder if provided
    download_dir = output_dir or settings_mgr.settings.download_dir

    async def _download():
        extractor_mgr = ExtractorManager()
        extractor_mgr.load_all()
        
        db_mgr = DatabaseManager()
        await db_mgr.initialize()

        try:
            safe_echo(f"Analyzing {url}...")
            extractor = extractor_mgr.get_extractor_for_url(url)
            await extractor.analyze(url)

            # Choose format
            formats = extractor.get_available_formats()
            if not formats:
                raise ValueError("No formats found on the page.")

            selected_fmt = formats[0]
            if format_id:
                matched = next((f for f in formats if f["format_id"] == format_id), None)
                if matched:
                    selected_fmt = matched
                else:
                    safe_echo(f"Format '{format_id}' not found. Defaulting to first format.", fg=typer.colors.YELLOW)

            # Resolve paths
            filename = render_filename_template(
                settings_mgr.settings.filename_template,
                {
                    "title": extractor.get_title(),
                    "uploader": extractor.get_uploader(),
                    "upload_date": None,
                    "resolution": selected_fmt.get("resolution") or "unknown",
                    "ext": selected_fmt.get("ext") or "mp4",
                    "id": selected_fmt["format_id"]
                }
            )
            save_path = get_safe_destination_path(download_dir, filename)
            safe_echo(f"Destination: {save_path}")

            # Define terminal progress indicator callback
            last_pct = -1
            def progress_callback(download_id, metrics):
                nonlocal last_pct
                pct = int(metrics.get("progress", 0))
                if pct != last_pct:
                    last_pct = pct
                    speed = metrics.get("speed", 0.0) / (1024*1024) # MB/s
                    # Draw a text-based progress bar
                    bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
                    sys.stdout.write(f"\rDownloading: [{bar}] {pct}% | Speed: {speed:.2f} MB/s")
                    sys.stdout.flush()

            # Instantiate download managers
            queue_mgr = QueueManager(
                db_manager=db_mgr,
                max_concurrent=1,
                speed_limit=0,
                chunk_size=settings_mgr.settings.chunk_size,
                retry_count=settings_mgr.settings.retry_count
            )
            queue_mgr.on_progress_update = progress_callback
            queue_mgr.start()

            # Add and run task
            safe_echo("\nStarting streaming download...")
            download_id = await queue_mgr.add_download(
                url=url,
                title=extractor.get_title(),
                save_path=str(save_path),
                format_id=selected_fmt["format_id"],
                thumbnail_url=extractor.get_thumbnail(),
                duration=extractor.get_duration(),
                resolution=selected_fmt.get("resolution"),
                codec=selected_fmt.get("vcodec"),
                container=selected_fmt.get("ext"),
                headers=selected_fmt.get("headers") or {}
            )

            # Wait for downloader to complete
            while True:
                await asyncio.sleep(0.5)
                task = queue_mgr.tasks.get(download_id)
                if task and task.status in ("completed", "failed", "cancelled"):
                    safe_echo("\n")
                    if task.status == "completed":
                        safe_echo(f"Successfully downloaded file: {save_path}", fg=typer.colors.GREEN, bold=True)
                    else:
                        safe_echo(f"Download finished with status: {task.status}", fg=typer.colors.RED)
                    break
            
            await queue_mgr.stop()

        except Exception as e:
            safe_echo(f"\nDownload failed: {e}", fg=typer.colors.RED, err=True)

    asyncio.run(_download())

if __name__ == "__main__":
    # If launched with no arguments, run the GUI by default
    if len(sys.argv) == 1:
        settings_mgr = SettingsManager()
        setup_logger("INFO")
        logger.info("No arguments supplied. Defaulting to GUI mode...")
        run_gui(settings_mgr)
    else:
        cli_app()
