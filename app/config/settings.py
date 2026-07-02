import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

# Default download directory in the user's home folder
DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads" / "VideoDownloaderPro")
# Default path for the configuration file
DEFAULT_CONFIG_PATH = Path.home() / ".video_downloader_pro" / "settings.json"

class AppSettings(BaseModel):
    """Pydantic schema representing the application settings."""
    download_dir: str = Field(default=DEFAULT_DOWNLOAD_DIR, description="Directory where downloads are saved.")
    default_quality: str = Field(default="best", description="Default media quality to download (best, worst, audio_only, etc.).")
    concurrent_downloads: int = Field(default=3, ge=1, le=10, description="Number of maximum concurrent downloads.")
    retry_count: int = Field(default=3, ge=0, le=10, description="Number of automatic retries on failure.")
    chunk_size: int = Field(default=1024 * 1024, ge=4096, description="Chunk size in bytes for streaming downloads (default 1MB).")
    theme: str = Field(default="dark", description="Visual theme for the application GUI (dark, light, system).")
    proxy: Optional[str] = Field(default=None, description="Proxy server URL (e.g. http://127.0.0.1:8080).")
    ffmpeg_location: Optional[str] = Field(default=None, description="Custom path to the FFmpeg executable.")
    filename_template: str = Field(
        default="{title} - {resolution}.{ext}",
        description="Safe filename template with placeholders."
    )
    auto_update: bool = Field(default=True, description="Enable automatic checks for application updates.")

class SettingsManager:
    """Manager to load, save, and modify the application settings."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._settings = self.load()

    @property
    def settings(self) -> AppSettings:
        """Access the current application settings."""
        return self._settings

    def load(self) -> AppSettings:
        """Loads configuration from JSON file. Creates defaults if the file does not exist or is invalid."""
        if not self.config_path.exists():
            return self._create_default()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppSettings(**data)
        except Exception:
            # If JSON is corrupted or parsing fails, return default settings
            return self._create_default()

    def save(self) -> None:
        """Saves current settings back to the configuration JSON file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                # Use model_dump_json for Pydantic V2 compatibility
                f.write(self._settings.model_dump_json(indent=4))
        except Exception as e:
            # Fallback output, handled by logging in higher modules
            print(f"Error saving settings: {e}")

    def update(self, **kwargs) -> None:
        """Updates multiple settings and saves the config immediately."""
        # This will validate inputs through Pydantic field validation
        updated_data = self._settings.model_dump()
        updated_data.update(kwargs)
        
        # Instantiate a new object to perform validation
        self._settings = AppSettings(**updated_data)
        self.save()

    def reset(self) -> None:
        """Resets all settings to default values and saves the config."""
        self._settings = AppSettings()
        self.save()

    def _create_default(self) -> AppSettings:
        """Creates the default settings, creates folder, and saves them."""
        settings = AppSettings()
        self._settings = settings
        self.save()
        return settings
