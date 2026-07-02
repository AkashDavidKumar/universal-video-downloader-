import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QScrollArea, QTabWidget, QSplitter, QTextEdit,
    QMessageBox, QFrame
)
from PySide6.QtGui import QPixmap, QImage, QGuiApplication
from PySide6.QtCore import Qt, Slot, QThreadPool

from .styles import DARK_THEME_QSS, LIGHT_THEME_QSS
from .components import DownloadQueueCard, SettingsPanel, ImageLoadWorker
from .async_bridge import AsyncEngineManager
from ..config.settings import SettingsManager
from ..core.path_utils import render_filename_template, get_safe_destination_path

class MainWindow(QMainWindow):
    """The central user interface window for Video Downloader Pro."""

    def __init__(self, settings_mgr: SettingsManager, async_engine: AsyncEngineManager):
        super().__init__()
        self.settings_mgr = settings_mgr
        self.async_engine = async_engine
        
        self.setWindowTitle("Video Downloader Pro")
        self.resize(1100, 700)
        
        # Apply theme stylesheet
        theme = self.settings_mgr.settings.theme
        if theme == "light":
            self.setStyleSheet(LIGHT_THEME_QSS)
        else:
            self.setStyleSheet(DARK_THEME_QSS)

        # Main Layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Top Title/Header
        header_layout = QHBoxLayout()
        title_lbl = QLabel("Video Downloader Pro", self)
        title_lbl.setObjectName("titleLabel")
        header_layout.addWidget(title_lbl)
        
        self.theme_lbl = QLabel(f"Mode: {theme.capitalize()}", self)
        self.theme_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        header_layout.addWidget(self.theme_lbl, 0, Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(header_layout)

        # Tab Widget
        self.tabs = QTabWidget(self)
        main_layout.addWidget(self.tabs)

        # 1. Main Downloader Tab
        downloader_tab = QWidget()
        self.tabs.addTab(downloader_tab, "Downloader")
        self._setup_downloader_tab(downloader_tab)

        # 2. Settings Tab
        self.settings_panel = SettingsPanel(self.settings_mgr, self)
        self.tabs.addTab(self.settings_panel, "Settings")

        # Connect slots
        self._connect_signals()
        
        # Store metadata from the last successful analysis
        self._current_metadata: Optional[Dict[str, Any]] = None
        
        # Keep track of active queue card widgets
        self.queue_cards: Dict[int, DownloadQueueCard] = {}

        # Clipboard Auto-monitoring
        self._check_clipboard_for_url()

    def _setup_downloader_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # URL Input Bar
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Paste video page URL here (e.g. https://mockvideo.com/watch/1)...")
        url_layout.addWidget(self.url_input)
        
        self.paste_btn = QPushButton("Paste", self)
        self.paste_btn.setObjectName("secondaryBtn")
        self.paste_btn.clicked.connect(self._paste_clipboard)
        url_layout.addWidget(self.paste_btn)

        self.analyze_btn = QPushButton("Analyze Page", self)
        self.analyze_btn.setObjectName("primaryBtn")
        self.analyze_btn.clicked.connect(self._analyze_url)
        url_layout.addWidget(self.analyze_btn)

        from PySide6.QtCore import Qt, Slot, QThreadPool, QPropertyAnimation
        self.analyze_btn_animation = QPropertyAnimation(self.analyze_btn, b"geometry")
        self.analyze_btn_animation.setDuration(200)
        self.analyze_btn_animation.setStartValue(self.analyze_btn.geometry())
        # Slightly shrink then restore
        rect = self.analyze_btn.geometry()
        shrink_rect = rect.adjusted(2, 2, -2, -2)
        self.analyze_btn_animation.setKeyValueAt(0.5, shrink_rect)
        self.analyze_btn_animation.setEndValue(rect)

        layout.addLayout(url_layout)

        # Main splitter (Details Left / Active Queue Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, stretch=1)

        # --- LEFT PANEL: Analysis Details ---
        self.detail_panel = QFrame()
        self.detail_panel.setObjectName("detailPanel")
        detail_layout = QVBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        detail_layout.setSpacing(10)
        
        detail_header = QLabel("Media Analysis Results", self)
        detail_header.setObjectName("headerText")
        detail_layout.addWidget(detail_header)

        # Media Thumbnail & Title Preview
        media_header_layout = QHBoxLayout()
        self.media_thumb = QLabel(self)
        self.media_thumb.setFixedSize(140, 80)
        self.media_thumb.setStyleSheet("background-color: #0F172A; border-radius: 6px;")
        self.media_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_thumb.setText("Preview")
        media_header_layout.addWidget(self.media_thumb)

        media_meta_layout = QVBoxLayout()
        self.media_title = QLabel("Analyze a URL to display media options.", self)
        self.media_title.setWordWrap(True)
        self.media_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        media_meta_layout.addWidget(self.media_title)
        
        self.media_uploader = QLabel("", self)
        self.media_uploader.setStyleSheet("color: #94A3B8; font-size: 12px;")
        media_meta_layout.addWidget(self.media_uploader)
        
        self.media_duration = QLabel("", self)
        self.media_duration.setStyleSheet("color: #38BDF8; font-size: 11px;")
        media_meta_layout.addWidget(self.media_duration)
        
        media_header_layout.addLayout(media_meta_layout, stretch=1)
        detail_layout.addLayout(media_header_layout)

        # Description Summary
        detail_layout.addWidget(QLabel("Description:", self))
        self.media_desc = QTextEdit(self)
        self.media_desc.setReadOnly(True)
        self.media_desc.setStyleSheet("background-color: #0F172A; border: 1px solid #334155; border-radius: 6px;")
        self.media_desc.setMaximumHeight(80)
        detail_layout.addWidget(self.media_desc)

        # Quality selection form
        quality_form = QHBoxLayout()
        quality_form.addWidget(QLabel("Select Stream:", self))
        self.format_combo = QComboBox(self)
        self.format_combo.setEnabled(False)
        self.format_combo.currentIndexChanged.connect(self._format_selected)
        quality_form.addWidget(self.format_combo, stretch=1)
        detail_layout.addLayout(quality_form)

        # Stream details label
        self.stream_details_lbl = QLabel("", self)
        self.stream_details_lbl.setStyleSheet("color: #38BDF8; font-size: 12px;")
        detail_layout.addWidget(self.stream_details_lbl)

        # Download path preview / Overrides
        save_layout = QHBoxLayout()
        self.save_preview_lbl = QLabel("Save Path Preview: --", self)
        self.save_preview_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.save_preview_lbl.setWordWrap(True)
        save_layout.addWidget(self.save_preview_lbl, stretch=1)
        detail_layout.addLayout(save_layout)

        # Action Buttons
        self.download_btn = QPushButton("Download Selected Stream", self)
        self.download_btn.setEnabled(False)
        self.download_btn.setStyleSheet("font-size: 14px; padding: 12px; background-color: #10B981;")
        self.download_btn.clicked.connect(self._start_download)
        detail_layout.addWidget(self.download_btn)
        
        splitter.addWidget(self.detail_panel)

        # --- RIGHT PANEL: Queue Monitor ---
        queue_panel = QFrame()
        queue_panel.setObjectName("queuePanel")
        queue_layout = QVBoxLayout(queue_panel)
        queue_layout.setContentsMargins(12, 12, 12, 12)
        
        queue_header = QLabel("Active Download Queue", self)
        queue_header.setObjectName("headerText")
        queue_layout.addWidget(queue_header)

        self.queue_scroll = QScrollArea(self)
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setStyleSheet("background: transparent; border: none;")
        
        self.queue_container = QWidget()
        self.queue_list_layout = QVBoxLayout(self.queue_container)
        self.queue_list_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_list_layout.setSpacing(8)
        self.queue_list_layout.addStretch()  # Keep cards pushed to top
        
        self.queue_scroll.setWidget(self.queue_container)
        queue_layout.addWidget(self.queue_scroll)
        
        splitter.addWidget(queue_panel)
        splitter.setSizes([550, 450])

    def _connect_signals(self) -> None:
        # Connect bridge events to slot handlers
        bridge = self.async_engine.bridge
        bridge.analysis_started.connect(self._on_analysis_started)
        bridge.analysis_completed.connect(self._on_analysis_completed)
        bridge.analysis_failed.connect(self._on_analysis_failed)
        bridge.download_progress.connect(self._on_download_progress)
        bridge.download_status_changed.connect(self._on_download_status_changed)

        # Connect settings panel trigger
        self.settings_panel.settings_saved.connect(self._on_settings_saved)

    def _paste_clipboard(self) -> None:
        clipboard = QGuiApplication.clipboard()
        self.url_input.setText(clipboard.text())

    def _check_clipboard_for_url(self) -> None:
        clipboard = QGuiApplication.clipboard()
        text = clipboard.text().strip()
        # Basic check for URLs
        if text.startswith(("http://", "https://")):
            self.url_input.setText(text)

    def _analyze_url(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter or paste a valid URL first.")
            return
            
        # Run background analysis coroutine
        self.async_engine.run_coroutine(self.async_engine.analyze_url_task(url))

    @Slot()
    def _on_analysis_started(self) -> None:
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing...")
        self.media_title.setText("Fetching video page details...")
        self.media_desc.clear()
        self.media_uploader.clear()
        self.media_duration.clear()
        self.format_combo.clear()
        self.format_combo.setEnabled(False)
        self.download_btn.setEnabled(False)

    @Slot(dict)
    def _on_analysis_completed(self, metadata: Dict[str, Any]) -> None:
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze Page")
        
        self._current_metadata = metadata
        
        # Populate Text Views
        self.media_title.setText(metadata["title"])
        self.media_uploader.setText(f"Uploaded by: {metadata['uploader']}")
        
        duration = metadata["duration"]
        if duration > 0:
            minutes, seconds = divmod(int(duration), 60)
            self.media_duration.setText(f"Duration: {minutes}m {seconds}s")
        else:
            self.media_duration.setText("Duration: Unknown")
            
        self.media_desc.setText(metadata["description"] or "No description available.")

        # Load Thumbnail image in background thread
        if metadata.get("thumbnail"):
            worker = ImageLoadWorker(metadata["thumbnail"])
            worker.signals.loaded.connect(self._set_media_thumbnail)
            QThreadPool.globalInstance().start(worker)
        else:
            self.media_thumb.setText("No Image")

        # Populate format list dropdown
        self.format_combo.setEnabled(True)
        for fmt in metadata["formats"]:
            res = fmt.get("resolution") or "unknown"
            ext = fmt.get("ext") or "mp4"
            size = fmt.get("filesize") or 0
            size_str = f"{size / (1024*1024):.1f} MB" if size > 0 else "unknown size"
            
            label = f"{res} ({ext}) - {size_str}"
            self.format_combo.addItem(label, fmt["format_id"])

        self.download_btn.setEnabled(True)
        self._format_selected()

    def _set_media_thumbnail(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            self.media_thumb.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.media_thumb.setPixmap(scaled)

    @Slot(str)
    def _on_analysis_failed(self, error_message: str) -> None:
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze Page")
        self.media_title.setText("Analysis Failed")
        QMessageBox.critical(self, "Analysis Failed", f"An error occurred while analyzing the page:\n{error_message}")

    @Slot()
    def _format_selected(self) -> None:
        if not self._current_metadata:
            return
            
        fmt_id = self.format_combo.currentData()
        fmt = next((f for f in self._current_metadata["formats"] if f["format_id"] == fmt_id), None)
        if not fmt:
            return

        # Render format details label
        vcodec = fmt.get("vcodec") or "unknown"
        acodec = fmt.get("acodec") or "unknown"
        fps = fmt.get("fps") or "N/A"
        fps_str = f" @ {fps}fps" if fps != "N/A" and fps else ""
        
        self.stream_details_lbl.setText(
            f"Video Codec: {vcodec}{fps_str} | Audio Codec: {acodec}"
        )

        # Update filename preview
        filename = render_filename_template(
            self.settings_mgr.settings.filename_template,
            {**self._current_metadata, **fmt}
        )
        self.save_preview_lbl.setText(f"Save Path Preview:\n{filename}")

    def _start_download(self) -> None:
        if not self._current_metadata:
            return

        fmt_id = self.format_combo.currentData()
        fmt = next((f for f in self._current_metadata["formats"] if f["format_id"] == fmt_id), None)
        if not fmt:
            return

        # 1. Compile final output filename
        filename = render_filename_template(
            self.settings_mgr.settings.filename_template,
            {**self._current_metadata, **fmt}
        )
        
        # 2. Get safe path (prevents traversal, adds incremental suffixes (1) etc.)
        try:
            save_path = get_safe_destination_path(
                download_dir=self.settings_mgr.settings.download_dir,
                filename=filename
            )
        except ValueError as e:
            QMessageBox.critical(self, "Invalid Path", str(e))
            return

        # 3. Request adding download to async queue
        # Since GUI runs on main thread, we submit coroutine to background event loop
        # and get future to retrieve download_id
        async def submit_download():
            headers = fmt.get("headers") or {}
            d_id = await self.async_engine.queue_mgr.add_download(
                url=self._current_metadata["url"],
                title=self._current_metadata["title"],
                save_path=str(save_path),
                format_id=fmt["format_id"],
                thumbnail_url=self._current_metadata["thumbnail"],
                duration=self._current_metadata["duration"],
                resolution=fmt.get("resolution"),
                codec=fmt.get("vcodec"),
                container=fmt.get("ext"),
                headers=headers
            )
            return d_id, str(save_path), fmt

        future = self.async_engine.run_coroutine(submit_download())
        
        # Wait for download registration
        try:
            download_id, path_str, format_data = future.result(timeout=2.0)
            
            # Create a card in the GUI Queue Panel
            size = format_data.get("filesize") or 0
            size_str = f"{size / (1024*1024):.1f} MB" if size > 0 else "Unknown Size"
            
            card = DownloadQueueCard(download_id, self._current_metadata["title"], size_str, self)
            card.pause_requested.connect(self._pause_download)
            card.resume_requested.connect(self._resume_download)
            card.cancel_requested.connect(self._cancel_download)
            
            # If thumbnail is available, trigger card thumbnail download
            if self._current_metadata.get("thumbnail"):
                card.load_thumbnail(self._current_metadata["thumbnail"])
                
            # Add to layout before stretch spacer
            # Remove stretch first, add card, re-add stretch
            self.queue_list_layout.insertWidget(self.queue_list_layout.count() - 1, card)
            self.queue_cards[download_id] = card
            
            # Switch view slightly or show status
            self.status_bar = self.statusBar()
            if self.status_bar:
                self.status_bar.showMessage(f"Download queued: {filename}", 3000)

        except Exception as e:
            QMessageBox.critical(self, "Queue Error", f"Failed to queue download: {e}")

    # --- Queue Controls forwarding ---
    def _pause_download(self, download_id: int) -> None:
        self.async_engine.run_coroutine(self.async_engine.queue_mgr.pause_download(download_id))

    def _resume_download(self, download_id: int) -> None:
        self.async_engine.run_coroutine(self.async_engine.queue_mgr.resume_download(download_id))

    def _cancel_download(self, download_id: int) -> None:
        self.async_engine.run_coroutine(self.async_engine.queue_mgr.cancel_download(download_id))

    # --- Bridge callbacks (Qt Slots on Main thread) ---
    @Slot(int, dict)
    def _on_download_progress(self, download_id: int, metrics: Dict[str, Any]) -> None:
        card = self.queue_cards.get(download_id)
        if card:
            card.update_progress(metrics)

    @Slot(int, str, str)
    def _on_download_status_changed(self, download_id: int, status: str, error: str) -> None:
        card = self.queue_cards.get(download_id)
        if card:
            card.update_progress({"status": status, "progress": card.progress_bar.value()})
            
        if status in ("completed", "failed", "cancelled"):
            # Show system tray notification / message box
            if status == "completed" and card:
                self.statusBar().showMessage(f"Download Completed: {card.title}", 5000)
            elif status == "failed":
                QMessageBox.warning(self, "Download Failed", f"Download ID {download_id} failed:\n{error}")

    # --- Shell integrations ---
    @Slot(str)
    def _open_file(self, save_path: str) -> None:
        if not save_path or not os.path.exists(save_path):
            QMessageBox.warning(self, "File Not Found", "The requested file no longer exists on disk.")
            return
            
        try:
            if sys.platform == "win32":
                os.startfile(save_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", save_path])
            else:
                subprocess.run(["xdg-open", save_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {e}")

    @Slot(str)
    def _open_folder(self, folder_path: str) -> None:
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(self, "Folder Not Found", "The folder path does not exist.")
            return
            
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder_path])
            else:
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open folder: {e}")

    @Slot()
    def _on_settings_saved(self) -> None:
        # Propagate settings adjustments back to active managers
        self.async_engine.queue_mgr.max_concurrent = self.settings_mgr.settings.concurrent_downloads
        self.async_engine.queue_mgr.chunk_size = self.settings_mgr.settings.chunk_size
        self.async_engine.queue_mgr.retry_count = self.settings_mgr.settings.retry_count
        
        # Check theme change
        theme = self.settings_mgr.settings.theme
        self.theme_lbl.setText(f"Mode: {theme.capitalize()}")
        if theme == "light":
            self.setStyleSheet(LIGHT_THEME_QSS)
        else:
            self.setStyleSheet(DARK_THEME_QSS)

    def closeEvent(self, event) -> None:
        # Gracefully stop background threads and loop
        self.async_engine.stop()
        event.accept()
