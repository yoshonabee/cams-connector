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

    def list_videos(
        self,
        camera: str,
        date: Optional[str] = None,
        hour: Optional[int] = None,
        page: int = 1,
        page_size: int = 60,
    ) -> tuple[list[VideoInfo], int]:
        """List video files for a camera with filtering and pagination.

        Directory structure: ~/recordings/<camera_name>/merged/YYYYmmdd_HH:MM.mp4

        Args:
            camera: Camera identifier
            date: Optional date filter in YYYYmmdd format
            hour: Optional hour filter (0-23)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (filtered and paginated videos list, total count)
        """
        videos: list[VideoInfo] = []

        # Camera directory
        camera_dir = self.recordings_dir / camera / "merged"

        if not camera_dir.exists():
            logger.warning(f"Camera directory does not exist: {camera_dir}")
            return [], 0

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

                        # Apply date filter
                        if date:
                            file_date_str = timestamp.strftime("%Y%m%d")
                            if file_date_str != date:
                                continue

                        # Apply hour filter
                        if hour is not None:
                            if timestamp.hour != hour:
                                continue

                    except Exception as e:
                        logger.warning(
                            f"Failed to parse timestamp from {filename}: {e}"
                        )
                        # Use file modification time as fallback
                        timestamp = datetime.fromtimestamp(stat.st_mtime)
                        timestamp_iso = timestamp.isoformat()

                        # If date/hour filter is specified but parsing failed, skip
                        if date or hour is not None:
                            continue

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

        # Calculate pagination
        total_count = len(videos)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_videos = videos[start_idx:end_idx]

        logger.info(
            f"Returning page {page} ({len(paginated_videos)} videos) "
            f"out of {total_count} total"
        )

        return paginated_videos, total_count

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
