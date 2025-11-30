"""FastAPI Proxy Server main application."""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Request,
    APIRouter,
    Query,
)
from typing import Optional
from fastapi.responses import StreamingResponse, Response

from config import settings
from models import (
    WSRequest,
    ListVideosPayload,
    ReadFilePayload,
    ErrorResponse,
    ListCamerasResponse,
)
from ws_manager import ws_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Proxy Server")
    yield
    logger.info("Shutting down Proxy Server")


app = FastAPI(
    title="CAMS Connector Proxy",
    description="Proxy server for Raspberry Pi video streaming",
    version="1.0.0",
    lifespan=lifespan,
)

router = APIRouter(prefix="/api")


# WebSocket endpoint for Pi devices
@router.websocket("/ws/device/{device_id}")
async def device_websocket(websocket: WebSocket, device_id: str):
    """WebSocket endpoint for Pi device connection."""

    # Accept connection
    await websocket.accept()

    # Authenticate device
    # Expected: first message should contain auth token
    try:
        auth_message = await websocket.receive_text()
        import json

        auth_data = json.loads(auth_message)

        if auth_data.get("token") != settings.DEVICE_TOKEN:
            await websocket.close(code=4001, reason="Invalid token")
            logger.warning(f"Device {device_id} failed authentication")
            return

        logger.info(f"Device {device_id} authenticated successfully")

    except Exception as e:
        await websocket.close(code=4000, reason="Auth failed")
        logger.error(f"Device {device_id} auth error: {e}")
        return

    # Register device
    device = await ws_manager.connect(device_id, websocket)

    try:
        # Keep connection alive (actual handling is in ws_manager)
        while True:
            # The receive loop is handled by ws_manager
            await device.receive_task

    except WebSocketDisconnect:
        logger.info(f"Device {device_id} disconnected")
    except Exception as e:
        logger.error(f"Error in device {device_id} connection: {e}")
    finally:
        await ws_manager.disconnect(device_id)


# HTTP API for clients
@router.get("/cameras", response_model=ListCamerasResponse)
async def list_cameras():
    """List all available cameras from all connected devices."""
    cameras = ws_manager.get_all_cameras()
    return ListCamerasResponse(cameras=cameras, total=len(cameras))


@router.get("/devices/{device_id}/videos")
async def list_videos(
    device_id: str,
    date: Optional[str] = Query(None, description="Date filter in YYYYmmdd format"),
    hour: Optional[int] = Query(None, description="Hour filter (0-23)", ge=0, le=23),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(60, description="Page size", ge=1, le=1000),
):
    """List available videos for a device/camera with filtering and pagination.

    Note: device_id can be either a device ID or a camera ID.
    The function will try to find the device by camera ID first.

    Args:
        device_id: Device or camera identifier
        date: Optional date filter in YYYYmmdd format
        hour: Optional hour filter (0-23)
        page: Page number (default: 1)
        page_size: Number of items per page (default: 60)
    """

    # Try to find device by camera ID first
    device = ws_manager.get_device_by_camera(device_id)

    # If not found, try to find by device ID (backward compatibility)
    if not device:
        device = ws_manager.get_device(device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device or camera not found")

    # Create request with filtering and pagination parameters
    request = WSRequest(
        id=str(uuid.uuid4()),
        type="LIST_VIDEOS",
        payload=ListVideosPayload(
            camera=device_id,
            date=date,
            hour=hour,
            page=page,
            page_size=page_size,
        ).model_dump(),
    )

    try:
        # Send request and wait for response
        response = await device.send_request(request)

        if response.type == "ERROR":
            error = ErrorResponse.model_validate(response.payload)
            raise HTTPException(status_code=500, detail=error.message)

        # Return video list with pagination info
        return response.payload

    except Exception as e:
        logger.error(f"Error listing videos for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.head("/devices/{device_id}/videos/{filename}")
@router.get("/devices/{device_id}/videos/{filename}")
async def stream_video(device_id: str, filename: str, request: Request):
    """Stream video file with Range support.

    Note: device_id can be either a device ID or a camera ID.
    The function will try to find the device by camera ID first.
    """

    # Try to find device by camera ID first
    device = ws_manager.get_device_by_camera(device_id)

    # If not found, try to find by device ID (backward compatibility)
    if not device:
        device = ws_manager.get_device(device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device or camera not found")

    # Parse Range header
    range_header = request.headers.get("range")
    start = None
    end = None
    is_head_request = request.method == "HEAD"

    if range_header:
        # Parse "bytes=start-end"
        try:
            range_str = range_header.replace("bytes=", "")
            if "-" in range_str:
                parts = range_str.split("-")
                start = int(parts[0]) if parts[0] else None
                end = int(parts[1]) if parts[1] else None
        except Exception as e:
            logger.warning(f"Failed to parse Range header: {e}")

    # For HEAD requests, only request first byte to get file size
    if is_head_request:
        start = 0
        end = 0

    # Create request
    ws_request = WSRequest(
        id=str(uuid.uuid4()),
        type="READ_FILE",
        payload=ReadFilePayload(
            camera=device_id, filename=filename, start=start, end=end
        ).model_dump(),
    )

    try:
        # Send request and get response with binary data
        response, chunks = await device.send_request_with_binary(ws_request)

        if response.type == "ERROR":
            error = ErrorResponse.model_validate(response.payload)
            raise HTTPException(status_code=500, detail=error.message)

        # Get file info from response
        file_size = response.payload.get("size", 0)
        content_start = response.payload.get("start", 0)
        content_end = response.payload.get("end", file_size - 1)

        # Prepare headers
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": "video/mp4",
        }

        # For HEAD requests, return only headers
        if is_head_request:
            headers["Content-Length"] = str(file_size)
            return Response(status_code=200, headers=headers)

        # Combine chunks for GET requests
        data = b"".join(chunks)

        # If range request, return 206 Partial Content
        if range_header:
            headers["Content-Range"] = (
                f"bytes {content_start}-{content_end}/{file_size}"
            )
            status_code = 206
        else:
            status_code = 200

        headers["Content-Length"] = str(len(data))

        async def stream_data():
            """Stream the data in chunks."""
            chunk_size = 64 * 1024  # 64KB
            for i in range(0, len(data), chunk_size):
                yield data[i : i + chunk_size]

        return StreamingResponse(
            stream_data(),
            status_code=status_code,
            headers=headers,
            media_type="video/mp4",
        )

    except Exception as e:
        logger.error(f"Error streaming video {filename} for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "connected_devices": len(ws_manager.connections)}


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
