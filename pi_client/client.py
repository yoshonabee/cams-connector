"""WebSocket client for Pi device."""

import asyncio
import json
import logging
from typing import Optional

import websockets
from websockets.client import WebSocketClientProtocol

from config import settings
from models import WSRequest, WSResponse, ListVideosPayload, ReadFilePayload
from file_handler import FileHandler

logger = logging.getLogger(__name__)


class PiClient:
    """WebSocket client for Raspberry Pi."""

    def __init__(self):
        """Initialize Pi client."""
        self.ws: Optional[WebSocketClientProtocol] = None
        self.file_handler = FileHandler()
        self.running = False

    async def connect(self):
        """Connect to proxy server with authentication."""
        logger.info(f"Connecting to {settings.PROXY_URL}")

        try:
            self.ws = await websockets.connect(
                settings.PROXY_URL,
                ping_interval=settings.PING_INTERVAL,
                ping_timeout=settings.PING_TIMEOUT,
            )

            # Send authentication
            auth_message = json.dumps({"token": settings.DEVICE_TOKEN})
            await self.ws.send(auth_message)

            logger.info("Connected and authenticated successfully")

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise

    async def disconnect(self):
        """Disconnect from proxy server."""
        if self.ws:
            await self.ws.close()
            self.ws = None
            logger.info("Disconnected from proxy")

    async def handle_list_videos(self, request: WSRequest) -> WSResponse:
        """Handle LIST_VIDEOS request.

        Args:
            request: Incoming request

        Returns:
            Response with video list
        """
        try:
            payload = ListVideosPayload.model_validate(request.payload)

            # List videos
            videos = self.file_handler.list_videos(payload.camera)

            return WSResponse(
                id=request.id,
                type="LIST_VIDEOS_RES",
                payload={
                    "videos": [v.model_dump() for v in videos],
                    "total": len(videos),
                },
            )

        except Exception as e:
            logger.error(f"Error handling LIST_VIDEOS: {e}")
            return WSResponse(
                id=request.id,
                type="ERROR",
                payload={"error": "LIST_VIDEOS_FAILED", "message": str(e)},
            )

    async def handle_read_file(self, request: WSRequest):
        """Handle READ_FILE request.

        Sends JSON response followed by binary data chunks.

        Args:
            request: Incoming request
        """
        try:
            payload = ReadFilePayload.model_validate(request.payload)

            # Read file
            data, file_size, actual_start, actual_end = (
                self.file_handler.read_file_chunk(
                    camera=payload.camera,
                    filename=payload.filename,
                    start=payload.start,
                    end=payload.end,
                )
            )

            # Send JSON response first
            response = WSResponse(
                id=request.id,
                type="READ_FILE_RES",
                payload={
                    "size": file_size,
                    "start": actual_start,
                    "end": actual_end,
                    "length": len(data),
                },
            )
            await self.ws.send(response.model_dump_json())

            # Send binary data in chunks
            chunk_size = settings.CHUNK_SIZE
            request_id_bytes = request.id.encode("utf-8")  # 36 bytes UUID

            for i in range(0, len(data), chunk_size):
                chunk = data[i : i + chunk_size]
                # Prefix with request ID
                message = request_id_bytes + chunk
                await self.ws.send(message)

            logger.info(f"Sent {len(data)} bytes for {payload.filename}")

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            response = WSResponse(
                id=request.id,
                type="ERROR",
                payload={"error": "FILE_NOT_FOUND", "message": str(e)},
            )
            await self.ws.send(response.model_dump_json())

        except Exception as e:
            logger.error(f"Error handling READ_FILE: {e}")
            response = WSResponse(
                id=request.id,
                type="ERROR",
                payload={"error": "READ_FILE_FAILED", "message": str(e)},
            )
            await self.ws.send(response.model_dump_json())

    async def handle_request(self, message: str):
        """Handle incoming request from proxy.

        Args:
            message: JSON request message
        """
        try:
            request = WSRequest.model_validate_json(message)
            logger.debug(f"Received request {request.id} type={request.type}")

            if request.type == "LIST_VIDEOS":
                response = await self.handle_list_videos(request)
                await self.ws.send(response.model_dump_json())

            elif request.type == "READ_FILE":
                await self.handle_read_file(request)

            else:
                logger.warning(f"Unknown request type: {request.type}")
                response = WSResponse(
                    id=request.id,
                    type="ERROR",
                    payload={
                        "error": "UNKNOWN_REQUEST",
                        "message": f"Unknown request type: {request.type}",
                    },
                )
                await self.ws.send(response.model_dump_json())

        except Exception as e:
            logger.error(f"Error handling request: {e}")

    async def receive_loop(self):
        """Main receive loop."""
        try:
            async for message in self.ws:
                if not self.running:
                    logger.info("Stopping receive loop")
                    break
                if isinstance(message, str):
                    await self.handle_request(message)
                else:
                    logger.warning("Received unexpected binary message from proxy")

        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by proxy")
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")

    async def run(self):
        """Run the client with auto-reconnect."""
        self.running = True

        while self.running:
            try:
                await self.connect()
                await self.receive_loop()

            except Exception as e:
                logger.error(f"Client error: {e}")

            finally:
                await self.disconnect()

            if self.running:
                logger.info(f"Reconnecting in {settings.RECONNECT_DELAY} seconds...")
                # Use sleep that can be interrupted by checking self.running
                for _ in range(settings.RECONNECT_DELAY * 10):  # Check every 0.1 seconds
                    if not self.running:
                        break
                    await asyncio.sleep(0.1)

    def stop(self):
        """Stop the client."""
        self.running = False
