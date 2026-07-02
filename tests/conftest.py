import asyncio
import pytest
from pathlib import Path
from app.config.settings import SettingsManager
from app.database.db_manager import DatabaseManager

@pytest.fixture
def temp_dir(tmp_path) -> Path:
    """Fixture supplying a temporary directory."""
    return tmp_path

@pytest.fixture
def test_settings(temp_dir) -> SettingsManager:
    """Fixture supplying a SettingsManager configured to use a temporary directory."""
    config_file = temp_dir / "test_settings.json"
    mgr = SettingsManager(config_path=config_file)
    mgr.update(download_dir=str(temp_dir / "downloads"))
    return mgr

@pytest.fixture
async def test_db(temp_dir) -> DatabaseManager:
    """Fixture supplying an initialized database in a temporary directory."""
    db_file = temp_dir / "test_database.db"
    db_mgr = DatabaseManager(db_path=db_file)
    await db_mgr.initialize()
    return db_mgr
