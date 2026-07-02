import pytest
from pathlib import Path
from app.core.path_utils import sanitize_filename, render_filename_template, get_safe_destination_path

def test_sanitize_filename():
    """Verifies that reserved characters are replaced and length truncated."""
    assert sanitize_filename("hello/world?.mp4") == "hello_world_.mp4"
    assert sanitize_filename("   leading  trailing.mp4   ") == "leading trailing.mp4"
    assert sanitize_filename("CON.mp4") == "safe_CON.mp4"
    
    # Very long name
    long_name = "a" * 300 + ".mp4"
    sanitized_long = sanitize_filename(long_name)
    assert len(sanitized_long) <= 240
    assert sanitized_long.endswith(".mp4")

def test_render_filename_template():
    """Verifies placeholder replacements in templates."""
    metadata = {
        "title": "A Great Video",
        "resolution": "1080p",
        "ext": "mkv",
        "uploader": "Creator",
        "id": "12345"
    }
    
    result = render_filename_template("{title} [{id}] - {resolution}.{ext}", metadata)
    assert result == "A Great Video [12345] - 1080p.mkv"

def test_path_traversal_prevention(temp_dir):
    """Verifies that directory traversal targets raise ValueErrors."""
    # Attempt to save file outside temp_dir using relative path
    traversal_name = "../../../etc/passwd"
    
    with pytest.raises(ValueError, match="directory traversal detected"):
        get_safe_destination_path(str(temp_dir), traversal_name)

def test_collision_resolution(temp_dir):
    """Verifies that file collisions auto-append index suffixes."""
    filename = "test_file.mp4"
    file_path = temp_dir / filename
    file_path.touch()
    
    safe_path1 = get_safe_destination_path(str(temp_dir), filename, prevent_overwrite=True)
    assert safe_path1.name == "test_file (1).mp4"
    
    # Touch this secondary path to simulate another collision
    safe_path1.touch()
    safe_path2 = get_safe_destination_path(str(temp_dir), filename, prevent_overwrite=True)
    assert safe_path2.name == "test_file (2).mp4"
