"""Data models for WebSocket communication (Pi side)."""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# Request Types (from Proxy)
RequestType = Literal["LIST_VIDEOS", "READ_FILE"]
ResponseType = Literal["LIST_VIDEOS_RES", "READ_FILE_RES", "ERROR"]


class WSRequest(BaseModel):
    """WebSocket request from Proxy."""

    id: str = Field(..., description="Unique request ID (UUID)")
    type: RequestType = Field(..., description="Request type")
    payload: dict[str, Any] = Field(default_factory=dict, description="Request payload")


class WSResponse(BaseModel):
    """WebSocket response to Proxy."""

    id: str = Field(..., description="Request ID this response corresponds to")
    type: ResponseType = Field(..., description="Response type")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Response payload"
    )


class ListVideosPayload(BaseModel):
    """Payload for LIST_VIDEOS request."""

    camera: str = Field(..., description="Camera identifier")


class ReadFilePayload(BaseModel):
    """Payload for READ_FILE request."""

    camera: str = Field(..., description="Camera identifier")
    filename: str = Field(..., description="Video filename")
    start: Optional[int] = Field(None, description="Start byte position")
    end: Optional[int] = Field(None, description="End byte position")


class VideoInfo(BaseModel):
    """Video file information."""

    filename: str
    size: int
    timestamp: str  # ISO format
    camera: str
