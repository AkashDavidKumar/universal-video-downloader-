import pytest
from pydantic import ValidationError
from app.config.settings import AppSettings, SettingsManager

def test_default_settings(test_settings):
    """Verifies default setting parameters are correctly set and loaded."""
    settings = test_settings.settings
    assert settings.default_quality == "best"
    assert settings.concurrent_downloads == 3
    assert settings.retry_count == 3
    assert settings.theme == "dark"

def test_settings_validation(test_settings):
    """Verifies that field boundary validation behaves correctly."""
    # Invalid concurrent downloads
    with pytest.raises(ValidationError):
        test_settings.update(concurrent_downloads=20)  # Must be <= 10

    # Invalid retry count
    with pytest.raises(ValidationError):
        test_settings.update(retry_count=-1)  # Must be >= 0

def test_settings_save_and_load(temp_dir):
    """Verifies settings load/save roundtrips to file."""
    config_file = temp_dir / "custom_settings.json"
    mgr = SettingsManager(config_path=config_file)
    
    mgr.update(theme="light", default_quality="audio_only")
    
    # Reload from file
    new_mgr = SettingsManager(config_path=config_file)
    assert new_mgr.settings.theme == "light"
    assert new_mgr.settings.default_quality == "audio_only"
