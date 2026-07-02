import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from loguru import logger

def find_ffmpeg(custom_path: Optional[str] = None) -> Optional[Path]:
    """Attempts to find the FFmpeg executable in the custom path or system PATH.
    
    Returns:
        Path to the FFmpeg executable, or None if not found.
    """
    if custom_path:
        path = Path(custom_path)
        # Check if custom path is a directory containing ffmpeg
        if path.is_dir():
            for exe in ("ffmpeg", "ffmpeg.exe"):
                full_path = path / exe
                if full_path.exists() and os.access(full_path, os.X_OK):
                    return full_path
        elif path.exists() and os.access(path, os.X_OK):
            return path

    # Search in system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return Path(system_ffmpeg)

    return None

async def verify_ffmpeg(ffmpeg_path: Path) -> Tuple[bool, str]:
    """Runs a process check to verify if FFmpeg can execute and returns its version.
    
    Args:
        ffmpeg_path: The Path to the FFmpeg executable.
        
    Returns:
        A tuple of (success_boolean, version_string_or_error).
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            str(ffmpeg_path),
            "-version",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            version_line = stdout.decode("utf-8", errors="ignore").split("\n")[0]
            return True, version_line
        else:
            return False, stderr.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"FFmpeg verification failed: {e}")
        return False, str(e)

async def merge_streams(
    ffmpeg_path: Path,
    video_path: Path,
    audio_path: Path,
    output_path: Path
) -> Tuple[bool, str]:
    """Merges separate video and audio files into a single video file.
    
    Args:
        ffmpeg_path: Path to FFmpeg executable.
        video_path: Path to the temporary video file.
        audio_path: Path to the temporary audio file.
        output_path: Final merged video output path.
        
    Returns:
        A tuple of (success_boolean, error_or_success_message).
    """
    if not video_path.exists() or not audio_path.exists():
        return False, f"Missing input file(s). Video: {video_path.exists()}, Audio: {audio_path.exists()}"

    # Build the merge command
    # -y overwrites output
    # -c:v copy copies video stream without re-encoding
    # -c:a aac encodes audio to AAC (or copy if compatible)
    # -map maps video from input 0 and audio from input 1
    cmd = [
        str(ffmpeg_path),
        "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        str(output_path)
    ]
    
    logger.info(f"Running FFmpeg merge: {' '.join(cmd)}")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            logger.info(f"FFmpeg merge completed successfully for: {output_path}")
            return True, "Success"
        else:
            err_msg = stderr.decode("utf-8", errors="ignore")
            logger.error(f"FFmpeg merge failed with code {proc.returncode}: {err_msg}")
            return False, err_msg
    except Exception as e:
        logger.error(f"Failed to run FFmpeg command: {e}")
        return False, str(e)
