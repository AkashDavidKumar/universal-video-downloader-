import os
import httpx
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QComboBox,
    QFileDialog, QSpinBox, QFormLayout, QGroupBox, QMessageBox
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QRunnable, QThreadPool, Signal, QObject

class ImageLoadSignals(QObject):
    loaded = Signal(QPixmap)

class ImageLoadWorker(QRunnable):
    """Runnable worker to load images from URL in a background thread."""
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.signals = ImageLoadSignals()

    def run(self) -> None:
        if not self.url or not self.url.startswith("http"):
            return
        try:
            # Fetch image bytes
            response = httpx.get(self.url, timeout=5.0)
            if response.status_code == 200:
                image = QImage()
                if image.loadFromData(response.content):
                    pixmap = QPixmap.fromImage(image)
                    self.signals.loaded.emit(pixmap)
        except Exception:
            # Silently ignore thumbnail download errors to maintain stability
            pass

class DownloadQueueCard(QWidget):
    """A card representation of an active, queued, or paused download item."""
    
    pause_requested = Signal(int)
    resume_requested = Signal(int)
    cancel_requested = Signal(int)

    def __init__(self, download_id: int, title: str, size_str: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.download_id = download_id
        self.title = title
        
        self.setObjectName("queueCard")
        self.setStyleSheet("""
            QWidget#queueCard {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px;
            }
        """)

        # Layouts
        card_layout = QHBoxLayout(self)
        card_layout.setContentsMargins(8, 8, 8, 8)
        
        # 1. Video Thumbnail
        self.thumb_label = QLabel(self)
        self.thumb_label.setFixedSize(96, 54)
        self.thumb_label.setStyleSheet("background-color: #0F172A; border-radius: 4px;")
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setText("No Image")
        card_layout.addWidget(self.thumb_label)

        # 2. Text & Progress Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        self.title_lbl = QLabel(title, self)
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #F8FAFC;")
        self.title_lbl.setWordWrap(False)
        info_layout.addWidget(self.title_lbl)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        info_layout.addWidget(self.progress_bar)

        # Status text layout
        status_layout = QHBoxLayout()
        self.status_lbl = QLabel("Queued", self)
        self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        
        self.metrics_lbl = QLabel(f"Size: {size_str} | Speed: 0 KB/s | ETA: --", self)
        self.metrics_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")
        self.metrics_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        status_layout.addWidget(self.status_lbl)
        status_layout.addWidget(self.metrics_lbl)
        info_layout.addLayout(status_layout)
        
        card_layout.addLayout(info_layout, stretch=1)

        # 3. Actions / Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(4)
        
        self.pause_btn = QPushButton("Pause", self)
        self.pause_btn.setObjectName("actionBtn_pause")
        self.pause_btn.clicked.connect(lambda: self.pause_requested.emit(self.download_id))
        
        self.resume_btn = QPushButton("Resume", self)
        self.resume_btn.setObjectName("actionBtn_resume")
        self.resume_btn.setVisible(False)
        self.resume_btn.clicked.connect(lambda: self.resume_requested.emit(self.download_id))
        
        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setObjectName("actionBtn_cancel")
        self.cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(self.download_id))

        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.resume_btn)
        controls_layout.addWidget(self.cancel_btn)
        card_layout.addLayout(controls_layout)

    def load_thumbnail(self, url: str) -> None:
        """Fetches the thumbnail from URL in a background thread."""
        worker = ImageLoadWorker(url)
        worker.signals.loaded.connect(self._set_thumbnail)
        QThreadPool.globalInstance().start(worker)

    def _set_thumbnail(self, pixmap: QPixmap) -> None:
        scaled_pixmap = pixmap.scaled(
            self.thumb_label.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        self.thumb_label.setPixmap(scaled_pixmap)

    def update_progress(self, metrics: Dict[str, Any]) -> None:
        """Updates the card's progress bar and text fields."""
        status = metrics.get("status", "downloading")
        progress = metrics.get("progress", 0.0)
        speed = metrics.get("speed", 0.0)
        eta = metrics.get("eta", 0.0)
        downloaded = metrics.get("downloaded_bytes", 0)
        total = metrics.get("total_bytes", 0)

        # Format stats
        mb_total = total / (1024 * 1024)
        mb_down = downloaded / (1024 * 1024)
        speed_mb = speed / (1024 * 1024)

        self.progress_bar.setValue(int(progress))
        self.status_lbl.setText(status.capitalize())

        # Format Speed and ETA
        speed_str = f"{speed_mb:.2f} MB/s" if speed_mb >= 0.1 else f"{speed / 1024:.1f} KB/s"
        eta_str = f"{int(eta)}s" if eta > 0 else "--"
        
        self.metrics_lbl.setText(
            f"{mb_down:.1f}MB / {mb_total:.1f}MB | Speed: {speed_str} | ETA: {eta_str}"
        )

        if status == "paused":
            self.pause_btn.setVisible(False)
            self.resume_btn.setVisible(True)
            self.status_lbl.setStyleSheet("color: #EAB308; font-size: 11px;")
        elif status == "downloading":
            self.pause_btn.setVisible(True)
            self.resume_btn.setVisible(False)
            self.status_lbl.setStyleSheet("color: #22C55E; font-size: 11px;")
        elif status == "completed":
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)
            self.status_lbl.setText("Completed")
            self.status_lbl.setStyleSheet("color: #10B981; font-size: 11px;")
        elif status == "failed":
            self.pause_btn.setVisible(False)
            self.resume_btn.setVisible(False)
            self.status_lbl.setText("Failed")
            self.status_lbl.setStyleSheet("color: #EF4444; font-size: 11px;")


class HistoryPanel(QWidget):
    """Dashboard to search, filter, and sort completed download history."""
    
    open_file_requested = Signal(str)  # Emits save_path
    open_folder_requested = Signal(str) # Emits directory path
    delete_requested = Signal(int)      # Emits download_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 1. Search and Filter Bar
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search history by title or URL...")
        self.search_input.textChanged.connect(self._trigger_filter)
        filter_layout.addWidget(self.search_input)

        self.filter_combo = QComboBox(self)
        self.filter_combo.addItems(["All Downloads", "Completed", "Failed", "Cancelled"])
        self.filter_combo.currentIndexChanged.connect(self._trigger_filter)
        filter_layout.addWidget(self.filter_combo)

        self.sort_combo = QComboBox(self)
        self.sort_combo.addItems(["Date Descending", "Date Ascending", "Title A-Z", "Size"])
        self.sort_combo.currentIndexChanged.connect(self._trigger_filter)
        filter_layout.addWidget(self.sort_combo)
        
        layout.addLayout(filter_layout)

        # 2. History Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Status", "Resolution", "Size", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.table)
        self._raw_history: list = []

    def populate(self, history: list) -> None:
        """Loads download items into the history dashboard."""
        self._raw_history = history
        self._apply_filter_sort()

    def _trigger_filter(self) -> None:
        self._apply_filter_sort()

    def _apply_filter_sort(self) -> None:
        search_query = self.search_input.text().lower()
        filter_val = self.filter_combo.currentText().lower()
        sort_val = self.sort_combo.currentText()

        # 1. Filter
        filtered = []
        for item in self._raw_history:
            title = (item.get("title") or "").lower()
            url = (item.get("url") or "").lower()
            status = (item.get("status") or "").lower()
            
            # Query match
            if search_query and search_query not in title and search_query not in url:
                continue
                
            # Status match
            if filter_val != "all downloads" and status != filter_val:
                continue
                
            filtered.append(item)

        # 2. Sort
        if sort_val == "Date Descending":
            filtered.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        elif sort_val == "Date Ascending":
            filtered.sort(key=lambda x: x.get("created_at") or "", reverse=False)
        elif sort_val == "Title A-Z":
            filtered.sort(key=lambda x: (x.get("title") or "").lower())
        elif sort_val == "Size":
            filtered.sort(key=lambda x: x.get("total_bytes") or 0, reverse=True)

        # Populate Table
        self.table.setRowCount(len(filtered))
        for row, item in enumerate(filtered):
            download_id = item.get("id", 0)
            title = item.get("title") or "Unknown Video"
            status = item.get("status") or "Unknown"
            res = item.get("resolution") or "N/A"
            
            total_bytes = item.get("total_bytes") or 0
            size_str = f"{total_bytes / (1024*1024):.1f} MB" if total_bytes > 0 else "Unknown"
            
            # Create cells
            self.table.setItem(row, 0, QTableWidgetItem(str(download_id)))
            self.table.setItem(row, 1, QTableWidgetItem(title))
            
            status_item = QTableWidgetItem(status.capitalize())
            if status == "completed":
                status_item.setForeground(Qt.GlobalColor.green)
            elif status == "failed":
                status_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 2, status_item)
            
            self.table.setItem(row, 3, QTableWidgetItem(res))
            self.table.setItem(row, 4, QTableWidgetItem(size_str))

            # Action Buttons Layout
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(2)
            
            save_path = item.get("save_path")
            
            open_file_btn = QPushButton("Open File")
            open_file_btn.setStyleSheet("font-size: 11px; padding: 2px 6px;")
            open_file_btn.setEnabled(status == "completed" and bool(save_path) and os.path.exists(save_path))
            open_file_btn.clicked.connect(lambda checked=False, path=save_path: self.open_file_requested.emit(path))
            
            open_folder_btn = QPushButton("Folder")
            open_folder_btn.setStyleSheet("font-size: 11px; padding: 2px 6px; background-color: #334155;")
            open_folder_btn.setEnabled(bool(save_path))
            open_folder_btn.clicked.connect(lambda checked=False, path=save_path: self.open_folder_requested.emit(str(Path(path).parent) if path else ""))
            
            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet("font-size: 11px; padding: 2px 6px; background-color: #EF4444;")
            del_btn.clicked.connect(lambda checked=False, d_id=download_id: self.delete_requested.emit(d_id))

            actions_layout.addWidget(open_file_btn)
            actions_layout.addWidget(open_folder_btn)
            actions_layout.addWidget(del_btn)
            
            self.table.setCellWidget(row, 5, actions_widget)


class SettingsPanel(QWidget):
    """Settings form to customize folders, defaults, theme, proxy, and templates."""
    
    settings_saved = Signal()

    def __init__(self, settings_mgr: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings_mgr = settings_mgr
        
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # 1. Download Path
        path_layout = QHBoxLayout()
        self.download_dir_input = QLineEdit(self)
        self.download_dir_input.setText(settings_mgr.settings.download_dir)
        path_layout.addWidget(self.download_dir_input)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_folder)
        path_layout.addWidget(browse_btn)
        form_layout.addRow("Download Folder:", path_layout)

        # 2. Quality options
        self.quality_combo = QComboBox(self)
        self.quality_combo.addItems(["best", "worst", "highest_resolution", "lowest_resolution", "audio_only"])
        self.quality_combo.setCurrentText(settings_mgr.settings.default_quality)
        form_layout.addRow("Default Quality:", self.quality_combo)

        # 3. Concurrent downloads
        self.concurrent_spin = QSpinBox(self)
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setValue(settings_mgr.settings.concurrent_downloads)
        form_layout.addRow("Max Concurrent Downloads:", self.concurrent_spin)

        # 4. Retries
        self.retry_spin = QSpinBox(self)
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(settings_mgr.settings.retry_count)
        form_layout.addRow("Retry Count:", self.retry_spin)

        # 5. Chunk Size
        self.chunk_combo = QComboBox(self)
        self.chunk_combo.addItem("512 KB", 512 * 1024)
        self.chunk_combo.addItem("1 MB (Default)", 1024 * 1024)
        self.chunk_combo.addItem("2 MB", 2 * 1024 * 1024)
        self.chunk_combo.addItem("4 MB", 4 * 1024 * 1024)
        
        # Set current value
        idx = self.chunk_combo.findData(settings_mgr.settings.chunk_size)
        if idx >= 0:
            self.chunk_combo.setCurrentIndex(idx)
        form_layout.addRow("Chunk Size:", self.chunk_combo)

        # 6. Theme
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItems(["dark", "light", "system"])
        self.theme_combo.setCurrentText(settings_mgr.settings.theme)
        form_layout.addRow("Application Theme:", self.theme_combo)

        # 7. Filename Template
        self.template_input = QLineEdit(self)
        self.template_input.setText(settings_mgr.settings.filename_template)
        form_layout.addRow("Filename Template:", self.template_input)

        # 8. Proxy
        self.proxy_input = QLineEdit(self)
        self.proxy_input.setPlaceholderText("e.g. http://127.0.0.1:8080 (optional)")
        self.proxy_input.setText(settings_mgr.settings.proxy or "")
        form_layout.addRow("Proxy URL:", self.proxy_input)

        # 9. FFmpeg Path
        ffmpeg_layout = QHBoxLayout()
        self.ffmpeg_input = QLineEdit(self)
        self.ffmpeg_input.setPlaceholderText("Search path automatically if empty")
        self.ffmpeg_input.setText(settings_mgr.settings.ffmpeg_location or "")
        ffmpeg_layout.addWidget(self.ffmpeg_input)
        
        ffmpeg_browse_btn = QPushButton("Browse...")
        ffmpeg_browse_btn.clicked.connect(self._browse_ffmpeg)
        ffmpeg_layout.addWidget(ffmpeg_browse_btn)
        form_layout.addRow("FFmpeg Location:", ffmpeg_layout)

        main_layout.addLayout(form_layout)
        
        # Save Button
        save_btn = QPushButton("Save Settings", self)
        save_btn.clicked.connect(self._save_settings)
        main_layout.addWidget(save_btn)

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.download_dir_input.text())
        if folder:
            self.download_dir_input.setText(folder)

    def _browse_ffmpeg(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "Select FFmpeg Executable", "", "Executables (*.exe *ffmpeg*)")
        if file:
            self.ffmpeg_input.setText(file)

    def _save_settings(self) -> None:
        try:
            self.settings_mgr.update(
                download_dir=self.download_dir_input.text(),
                default_quality=self.quality_combo.currentText(),
                concurrent_downloads=self.concurrent_spin.value(),
                retry_count=self.retry_spin.value(),
                chunk_size=self.chunk_combo.currentData(),
                theme=self.theme_combo.currentText(),
                filename_template=self.template_input.text(),
                proxy=self.proxy_input.text().strip() or None,
                ffmpeg_location=self.ffmpeg_input.text().strip() or None
            )
            QMessageBox.information(self, "Success", "Settings saved successfully! Restart application if changing theme.")
            self.settings_saved.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
