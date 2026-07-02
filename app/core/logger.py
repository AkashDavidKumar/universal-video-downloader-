import sys
from pathlib import Path
from loguru import logger

# Default log file path
DEFAULT_LOG_DIR = Path.home() / ".video_downloader_pro" / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "app.log"

def setup_logger(log_level: str = "INFO", log_file: Path = DEFAULT_LOG_FILE) -> None:
    """Configures the Loguru logger.
    
    Sets up a colorized console output and a rotating file output.
    
    Args:
        log_level: Default logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to the log file.
    """
    # Create log directory if it doesn't exist
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Clear any default configuration
    logger.remove()
    
    # 1. Console Output Configuration
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        format=console_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 2. Rotating File Configuration
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} - "
        "{message}"
    )
    logger.add(
        str(log_file),
        format=file_format,
        level=log_level,
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="5 days",  # Keep logs for up to 5 days
        compression="zip",  # Compress rotated log files
        backtrace=True,
        diagnose=False,
        encoding="utf-8"
    )

    logger.info(f"Logger initialized. Level: {log_level}, File: {log_file}")
