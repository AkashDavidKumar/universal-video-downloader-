import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

# Regex to match reserved characters on Windows, macOS, and Linux: < > : " / \ | ? * and control chars
RESERVED_CHARS_RE = re.compile(r'[\x00-\x1f\\/:*?"<>|]')

def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """Sanitizes a string to make it a safe filename on Windows, Linux, and macOS.
    
    Args:
        filename: The original filename or string.
        replacement: Character to replace illegal characters with.
        
    Returns:
        Sanitized filename.
    """
    # Replace illegal characters
    sanitized = RESERVED_CHARS_RE.sub(replacement, filename)
    
    # Replace multiple replacement chars or spaces with a single one
    sanitized = re.sub(r'\s+', ' ', sanitized)
    sanitized = re.sub(f'{re.escape(replacement)}+', replacement, sanitized)
    
    # Strip leading/trailing spaces and dots (Windows doesn't allow trailing dots)
    sanitized = sanitized.strip(" .")
    
    # Handle empty filenames or reserved names
    if not sanitized:
        sanitized = "downloaded_file"
        
    # Windows reserved filenames (CON, PRN, AUX, NUL, COM1, LPT1, etc.)
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    stem = Path(sanitized).stem.upper()
    if stem in reserved_names:
        sanitized = f"safe_{sanitized}"
        
    # Truncate length to avoid path length limits (255 characters limit on most filesystems)
    # We truncate the stem while preserving the extension
    path_obj = Path(sanitized)
    ext = path_obj.suffix
    stem_limit = 240 - len(ext)
    if len(path_obj.stem) > stem_limit:
        sanitized = path_obj.stem[:stem_limit].strip() + ext
        
    return sanitized

def render_filename_template(
    template: str,
    metadata: Dict[str, Any],
    default_ext: str = "mp4"
) -> str:
    """Renders a template pattern into a safe sanitized filename.
    
    Supported placeholders:
    - {title}: Media title
    - {date}: Current date or upload date (YYYYMMDD)
    - {quality}: Resolution/format descriptor
    - {resolution}: Dimensions (e.g. 1920x1080)
    - {uploader}: Author/uploader name
    - {id}: Unique ID of the video/format
    
    Args:
        template: Template string, e.g. "{title} - {resolution}.{ext}"
        metadata: Available metadata dictionary.
        default_ext: Fallback file extension if not provided.
        
    Returns:
        Sanitized safe filename.
    """
    # Safe date generation
    date_val = metadata.get("upload_date")
    if not date_val:
        date_val = datetime.now().strftime("%Y%m%d")

    # Map placeholders to values, providing safe defaults
    placeholders = {
        "title": metadata.get("title") or "video",
        "date": date_val,
        "quality": metadata.get("quality") or "best",
        "resolution": metadata.get("resolution") or "unknown",
        "uploader": metadata.get("uploader") or "uploader",
        "id": metadata.get("id") or "media",
        "ext": metadata.get("ext") or default_ext
    }
    
    # We sanitize individual placeholder fields BEFORE inserting them into the template
    # to preserve template punctuation (like hyphens, spaces, brackets).
    sanitized_placeholders = {}
    for key, val in placeholders.items():
        if key == "ext":
            # Extension shouldn't have dots or slashes
            sanitized_placeholders[key] = re.sub(r'[^a-zA-Z0-9]', '', str(val))
        else:
            sanitized_placeholders[key] = sanitize_filename(str(val))
            
    # Format the template
    try:
        filename = template.format(**sanitized_placeholders)
    except KeyError as e:
        logger.warning(f"Template contains unknown placeholder: {e}. Falling back to default format.")
        filename = f"{sanitized_placeholders['title']} - {sanitized_placeholders['resolution']}.{sanitized_placeholders['ext']}"
    except Exception as e:
        logger.error(f"Failed to render filename template: {e}")
        filename = f"media_{sanitized_placeholders['id']}.{sanitized_placeholders['ext']}"
        
    return sanitize_filename(filename)

def get_safe_destination_path(
    download_dir: str,
    filename: str,
    prevent_overwrite: bool = True
) -> Path:
    """Validates the target directory, prevents path traversal, and returns a safe absolute path.
    
    If prevent_overwrite is True, appends incremental suffixes (1), (2), etc. if the file exists.
    
    Args:
        download_dir: The target download folder.
        filename: Sanitized target file name.
        prevent_overwrite: If True, resolves file conflicts by incrementing suffix.
        
    Returns:
        Safe absolute path inside download_dir.
        
    Raises:
        ValueError: If directory traversal is detected.
    """
    # 1. Resolve absolute paths
    base_path = Path(download_dir).resolve()
    target_path = (base_path / filename).resolve()
    
    # 2. Path Traversal Guard: Check if target path starts with the download directory path
    if not str(target_path).startswith(str(base_path)):
        logger.error(f"Path traversal attempt blocked: {target_path} is outside {base_path}")
        raise ValueError("Invalid target path: directory traversal detected.")
        
    # 3. Collision Resolution
    if prevent_overwrite and target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        counter = 1
        while target_path.exists():
            target_path = (base_path / f"{stem} ({counter}){suffix}").resolve()
            counter += 1
            
    return target_path
