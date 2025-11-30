"""Main entry point for Pi Client."""

import asyncio
import logging
import signal

from client import PiClient
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main function."""
    logger.info(f"Starting Pi Client for device: {settings.DEVICE_ID}")
    logger.info(f"Recordings directory: {settings.RECORDINGS_DIR}")

    # Create client
    client = PiClient()

    # Handle signals for graceful shutdown using asyncio
    loop = asyncio.get_running_loop()

    def signal_handler():
        """Async signal handler for graceful shutdown."""
        logger.info("Received shutdown signal")
        client.stop()
        # Close WebSocket connection to interrupt blocking operations
        if client.ws:
            asyncio.create_task(client.disconnect())

    # Register signal handlers
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)

    # Run client
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
