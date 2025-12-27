"""
WebSocket consumers for real-time updates.
Provides real-time progress updates for file conversions and processing.
"""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class ConversionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time conversion progress updates.

    Usage:
        ws://domain/ws/conversion/<task_id>/

    Messages sent to client:
        {
            "type": "progress",
            "progress": 45,  # 0-100
            "message": "Converting page 5 of 10...",
            "status": "processing"  # processing, completed, error
        }
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.task_id = self.scope["url_route"]["kwargs"]["task_id"]
        self.room_group_name = f"conversion_{self.task_id}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        logger.info(
            f"WebSocket connected: task_id={self.task_id}, "
            f"channel={self.channel_name}"
        )

        # Send initial connection message
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connected",
                    "task_id": self.task_id,
                    "message": "Connected to conversion progress updates",
                }
            )
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        logger.info(
            f"WebSocket disconnected: task_id={self.task_id}, " f"code={close_code}"
        )

    async def receive(self, text_data):
        """
        Handle messages from WebSocket client.
        Currently not used, but can be extended for client commands.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "ping":
                # Respond to ping with pong
                await self.send(
                    text_data=json.dumps(
                        {"type": "pong", "timestamp": data.get("timestamp")}
                    )
                )
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def conversion_progress(self, event):
        """
        Handle conversion progress updates from channel layer.

        Args:
            event: Dict with progress, message, status
        """
        # Send progress to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "type": "progress",
                    "progress": event.get("progress", 0),
                    "message": event.get("message", ""),
                    "status": event.get("status", "processing"),
                    "task_id": self.task_id,
                }
            )
        )

    async def conversion_completed(self, event):
        """
        Handle conversion completion.

        Args:
            event: Dict with download_url, filename, etc.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "completed",
                    "progress": 100,
                    "message": event.get("message", "Conversion completed"),
                    "status": "completed",
                    "task_id": self.task_id,
                    "download_url": event.get("download_url"),
                    "filename": event.get("filename"),
                    "file_size": event.get("file_size"),
                }
            )
        )

    async def conversion_error(self, event):
        """
        Handle conversion errors.

        Args:
            event: Dict with error message
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "error",
                    "progress": 0,
                    "message": event.get("message", "Conversion failed"),
                    "status": "error",
                    "task_id": self.task_id,
                    "error": event.get("error", "Unknown error"),
                }
            )
        )


class BatchConversionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for batch conversion progress updates.

    Usage:
        ws://domain/ws/batch/<batch_id>/

    Messages sent to client:
        {
            "type": "batch_progress",
            "total_files": 10,
            "completed_files": 5,
            "current_file": "document.pdf",
            "progress": 50,
            "message": "Processing file 5 of 10..."
        }
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.batch_id = self.scope["url_route"]["kwargs"]["batch_id"]
        self.room_group_name = f"batch_{self.batch_id}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        logger.info(
            f"WebSocket connected: batch_id={self.batch_id}, "
            f"channel={self.channel_name}"
        )

        # Send initial connection message
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connected",
                    "batch_id": self.batch_id,
                    "message": "Connected to batch conversion progress updates",
                }
            )
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        logger.info(
            f"WebSocket disconnected: batch_id={self.batch_id}, " f"code={close_code}"
        )

    async def receive(self, text_data):
        """Handle messages from WebSocket client."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "ping":
                await self.send(
                    text_data=json.dumps(
                        {"type": "pong", "timestamp": data.get("timestamp")}
                    )
                )

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def batch_progress(self, event):
        """
        Handle batch progress updates.

        Args:
            event: Dict with batch progress info
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "batch_progress",
                    "total_files": event.get("total_files", 0),
                    "completed_files": event.get("completed_files", 0),
                    "current_file": event.get("current_file", ""),
                    "progress": event.get("progress", 0),
                    "message": event.get("message", ""),
                    "status": event.get("status", "processing"),
                    "batch_id": self.batch_id,
                }
            )
        )

    async def batch_file_completed(self, event):
        """
        Handle individual file completion in batch.

        Args:
            event: Dict with file info
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "file_completed",
                    "filename": event.get("filename", ""),
                    "file_index": event.get("file_index", 0),
                    "message": event.get("message", ""),
                    "batch_id": self.batch_id,
                }
            )
        )

    async def batch_completed(self, event):
        """
        Handle batch completion.

        Args:
            event: Dict with download info
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "batch_completed",
                    "progress": 100,
                    "message": event.get("message", "Batch conversion completed"),
                    "status": "completed",
                    "batch_id": self.batch_id,
                    "download_url": event.get("download_url"),
                    "total_files": event.get("total_files", 0),
                    "successful_files": event.get("successful_files", 0),
                    "failed_files": event.get("failed_files", 0),
                }
            )
        )

    async def batch_error(self, event):
        """
        Handle batch errors.

        Args:
            event: Dict with error message
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "batch_error",
                    "message": event.get("message", "Batch conversion failed"),
                    "status": "error",
                    "batch_id": self.batch_id,
                    "error": event.get("error", "Unknown error"),
                }
            )
        )
