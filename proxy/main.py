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
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import settings
from models import (
    WSRequest,
    ListVideosPayload,
    ReadFilePayload,
    ErrorResponse,
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket endpoint for Pi devices
@app.websocket("/ws/device/{device_id}")
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
@app.get("/api/devices/{device_id}/videos")
async def list_videos(device_id: str):
    """List available videos for a device/camera."""

    # Get device connection
    device = ws_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not connected")

    # Create request
    request = WSRequest(
        id=str(uuid.uuid4()),
        type="LIST_VIDEOS",
        payload=ListVideosPayload(camera=device_id).model_dump(),
    )

    try:
        # Send request and wait for response
        response = await device.send_request(request)

        if response.type == "ERROR":
            error = ErrorResponse.model_validate(response.payload)
            raise HTTPException(status_code=500, detail=error.message)

        # Return video list
        return response.payload

    except Exception as e:
        logger.error(f"Error listing videos for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/devices/{device_id}/videos/{filename}")
async def stream_video(device_id: str, filename: str, request: Request):
    """Stream video file with Range support."""

    # Get device connection
    device = ws_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not connected")

    # Parse Range header
    range_header = request.headers.get("range")
    start = None
    end = None

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

        # Combine chunks
        data = b"".join(chunks)

        # Prepare headers
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": "video/mp4",
        }

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
