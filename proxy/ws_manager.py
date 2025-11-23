"""WebSocket connection manager for Pi devices."""

import asyncio
import logging
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from models import WSRequest, WSResponse

logger = logging.getLogger(__name__)


class PendingRequest:
    """Represents a pending request waiting for response."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.future: asyncio.Future = asyncio.Future()
        self.data_chunks: list[bytes] = []

    def set_response(self, response: WSResponse):
        """Set the JSON response."""
        if not self.future.done():
            self.future.set_result(response)

    def add_chunk(self, chunk: bytes):
        """Add a binary data chunk."""
        self.data_chunks.append(chunk)

    def set_error(self, error: Exception):
        """Set an error."""
        if not self.future.done():
            self.future.set_exception(error)


class DeviceConnection:
    """Represents a connected Pi device."""

    def __init__(self, device_id: str, websocket: WebSocket):
        self.device_id = device_id
        self.websocket = websocket
        self.pending_requests: dict[str, PendingRequest] = {}
        self.receive_task: Optional[asyncio.Task] = None

    async def send_request(self, request: WSRequest) -> WSResponse:
        """Send a request and wait for response."""
        pending = PendingRequest(request.id)
        self.pending_requests[request.id] = pending

        try:
            # Send JSON request
            await self.websocket.send_text(request.model_dump_json())
            logger.debug(f"Sent request {request.id} to device {self.device_id}")

            # Wait for response with timeout
            response = await asyncio.wait_for(pending.future, timeout=60.0)
            return response

        except asyncio.TimeoutError:
            logger.error(f"Request {request.id} timed out")
            raise
        finally:
            # Clean up
            self.pending_requests.pop(request.id, None)

    async def send_request_with_binary(
        self, request: WSRequest
    ) -> tuple[WSResponse, list[bytes]]:
        """Send a request and wait for response with binary data."""
        pending = PendingRequest(request.id)
        self.pending_requests[request.id] = pending

        try:
            # Send JSON request
            await self.websocket.send_text(request.model_dump_json())
            logger.debug(f"Sent request {request.id} to device {self.device_id}")

            # Wait for response with timeout
            response = await asyncio.wait_for(pending.future, timeout=60.0)
            return response, pending.data_chunks

        except asyncio.TimeoutError:
            logger.error(f"Request {request.id} timed out")
            raise
        finally:
            # Clean up
            self.pending_requests.pop(request.id, None)

    async def handle_message(self, message: str | bytes):
        """Handle incoming message from device."""
        if isinstance(message, str):
            # JSON response
            try:
                response = WSResponse.model_validate_json(message)
                logger.debug(
                    f"Received response {response.id} from device {self.device_id}"
                )

                # Find pending request and complete it
                pending = self.pending_requests.get(response.id)
                if pending:
                    pending.set_response(response)
                else:
                    logger.warning(
                        f"Received response for unknown request {response.id}"
                    )

            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")

        else:
            # Binary data: first 36 bytes are request ID (UUID string)
            if len(message) < 36:
                logger.warning("Received binary message too short for request ID")
                return

            request_id = message[:36].decode("utf-8")
            data = message[36:]

            logger.debug(f"Received {len(data)} bytes for request {request_id}")

            # Find pending request and add chunk
            pending = self.pending_requests.get(request_id)
            if pending:
                pending.add_chunk(data)
            else:
                logger.warning(f"Received binary data for unknown request {request_id}")


class WSManager:
    """Manages WebSocket connections from Pi devices."""

    def __init__(self):
        self.connections: dict[str, DeviceConnection] = {}

    async def connect(self, device_id: str, websocket: WebSocket) -> DeviceConnection:
        """Register a new device connection."""
        device = DeviceConnection(device_id, websocket)
        self.connections[device_id] = device

        # Start receiving messages
        device.receive_task = asyncio.create_task(self._receive_loop(device))

        logger.info(f"Device {device_id} connected")
        return device

    async def disconnect(self, device_id: str):
        """Remove a device connection."""
        device = self.connections.pop(device_id, None)
        if device:
            # Cancel receive task
            if device.receive_task:
                device.receive_task.cancel()

            # Fail all pending requests
            for pending in device.pending_requests.values():
                pending.set_error(Exception("Device disconnected"))

            logger.info(f"Device {device_id} disconnected")

    def get_device(self, device_id: str) -> Optional[DeviceConnection]:
        """Get a device connection by ID."""
        return self.connections.get(device_id)

    async def _receive_loop(self, device: DeviceConnection):
        """Continuously receive messages from device."""
        try:
            while True:
                # Receive text or bytes
                message = await device.websocket.receive()

                if "text" in message:
                    await device.handle_message(message["text"])
                elif "bytes" in message:
                    await device.handle_message(message["bytes"])

        except WebSocketDisconnect:
            logger.info(f"Device {device.device_id} disconnected (WebSocket closed)")
        except asyncio.CancelledError:
            logger.debug(f"Receive loop cancelled for device {device.device_id}")
        except Exception as e:
            logger.error(f"Error in receive loop for device {device.device_id}: {e}")
        finally:
            await self.disconnect(device.device_id)


# Global manager instance
ws_manager = WSManager()
