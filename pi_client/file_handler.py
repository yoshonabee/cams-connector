"""File system handler for video files."""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import settings
from models import VideoInfo

logger = logging.getLogger(__name__)


class FileHandler:
    """Handles file system operations for video files."""

    def __init__(self, recordings_dir: Optional[Path] = None):
        """Initialize file handler.

        Args:
            recordings_dir: Base directory for recordings. Defaults to settings.RECORDINGS_DIR
        """
        self.recordings_dir = recordings_dir or settings.RECORDINGS_DIR

    def list_videos(self, camera: str) -> list[VideoInfo]:
        """List all video files for a camera.

        Directory structure: ~/recordings/<camera_name>/merged/YYYYmmdd_HH:MM.mp4

        Args:
            camera: Camera identifier

        Returns:
            List of VideoInfo objects
        """
        videos: list[VideoInfo] = []

        # Camera directory
        camera_dir = self.recordings_dir / camera / "merged"

        if not camera_dir.exists():
            logger.warning(f"Camera directory does not exist: {camera_dir}")
            return videos

        # Scan for .mp4 files
        try:
            for file_path in camera_dir.glob("*.mp4"):
                if file_path.is_file():
                    stat = file_path.stat()

                    # Parse timestamp from filename (YYYYmmdd_HH:MM.mp4)
                    try:
                        filename = file_path.name
                        # Remove .mp4 extension
                        date_time_str = filename.replace(".mp4", "")
                        # Parse: YYYYmmdd_HH:MM
                        timestamp = datetime.strptime(date_time_str, "%Y%m%d_%H:%M")
                        timestamp_iso = timestamp.isoformat()
                    except Exception as e:
                        logger.warning(
                            f"Failed to parse timestamp from {filename}: {e}"
                        )
                        # Use file modification time as fallback
                        timestamp_iso = datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat()

                    videos.append(
                        VideoInfo(
                            filename=file_path.name,
                            size=stat.st_size,
                            timestamp=timestamp_iso,
                            camera=camera,
                        )
                    )

            logger.info(f"Found {len(videos)} videos for camera {camera}")

        except Exception as e:
            logger.error(f"Error listing videos for camera {camera}: {e}")

        # Sort by timestamp (newest first)
        videos.sort(key=lambda v: v.timestamp, reverse=True)

        return videos

    def read_file_chunk(
        self,
        camera: str,
        filename: str,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> tuple[bytes, int, int, int]:
        """Read a file or file chunk.

        Args:
            camera: Camera identifier
            filename: Video filename
            start: Start byte position (inclusive)
            end: End byte position (inclusive)

        Returns:
            Tuple of (data, file_size, actual_start, actual_end)

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If invalid range
        """
        # Build file path
        file_path = self.recordings_dir / camera / "merged" / filename

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file size
        file_size = file_path.stat().st_size

        # Determine actual range
        actual_start = start if start is not None else 0
        actual_end = end if end is not None else file_size - 1

        # Validate range
        if actual_start < 0 or actual_end >= file_size or actual_start > actual_end:
            raise ValueError(
                f"Invalid range: {actual_start}-{actual_end} (file size: {file_size})"
            )

        # Read data
        with open(file_path, "rb") as f:
            f.seek(actual_start)
            bytes_to_read = actual_end - actual_start + 1
            data = f.read(bytes_to_read)

        logger.debug(
            f"Read {len(data)} bytes from {filename} (range: {actual_start}-{actual_end})"
        )

        return data, file_size, actual_start, actual_end
