"""Utility for tracking active WebSocket connections."""

from typing import List

from fastapi import WebSocket


class ConnectionManager:
    """Track and broadcast messages to connected WebSocket clients."""

    def __init__(self) -> None:
        """Initialize the connection registry."""
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept an incoming WebSocket and register it.

        Args:
            websocket (WebSocket): WebSocket instance to accept.
        """
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket from the registry.

        Args:
            websocket (WebSocket): WebSocket instance to remove.
        """
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str) -> None:
        """
        Send a text message to every connected WebSocket.

        Args:
            message (str): Text payload to broadcast.
        """
        for connection in self.active_connections:
            await connection.send_text(message)
