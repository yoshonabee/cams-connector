"""Data models for WebSocket communication."""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# Request Types
RequestType = Literal["LIST_VIDEOS", "READ_FILE"]
ResponseType = Literal["LIST_VIDEOS_RES", "READ_FILE_RES", "ERROR"]


class WSRequest(BaseModel):
    """WebSocket request from Proxy to Pi."""

    id: str = Field(..., description="Unique request ID (UUID)")
    type: RequestType = Field(..., description="Request type")
    payload: dict[str, Any] = Field(default_factory=dict, description="Request payload")


class WSResponse(BaseModel):
    """WebSocket response from Pi to Proxy."""

    id: str = Field(..., description="Request ID this response corresponds to")
    type: ResponseType = Field(..., description="Response type")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Response payload"
    )


# Payload Models
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


class ListVideosResponse(BaseModel):
    """Response payload for LIST_VIDEOS."""

    videos: list[VideoInfo]
    total: int


class ErrorResponse(BaseModel):
    """Error response payload."""

    error: str
    message: str
