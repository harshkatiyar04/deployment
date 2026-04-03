from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections grouped by circle_id."""

    def __init__(self) -> None:
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, circle_id: str, ws: WebSocket, user_id: str) -> None:
        """Accept and register a WebSocket connection for a circle room."""
        await ws.accept()
        setattr(ws, "zenk_user_id", str(user_id))
        if circle_id not in self.rooms:
            self.rooms[circle_id] = []
        self.rooms[circle_id].append(ws)
        logger.info("WS connected to circle %s — total %d", circle_id, len(self.rooms[circle_id]))

    def disconnect(self, circle_id: str, ws: WebSocket) -> None:
        """Remove a WebSocket connection from a circle room."""
        if circle_id in self.rooms:
            try:
                self.rooms[circle_id].remove(ws)
            except ValueError:
                pass
            if not self.rooms[circle_id]:
                del self.rooms[circle_id]
        logger.info("WS disconnected from circle %s", circle_id)

    async def kick_user(self, circle_id: str, user_id: str, reason: str = None) -> None:
        """Forcefully disconnect a specific user from a circle if active."""
        if circle_id not in self.rooms:
            return
        
        target_id = str(user_id)
        to_remove = []
        for ws in self.rooms[circle_id]:
            if getattr(ws, "zenk_user_id", None) == target_id:
                to_remove.append(ws)
        
        for ws in to_remove:
            try:
                # Send reason payload if provided before closing
                if reason:
                    await ws.send_json({
                        "type": "error",
                        "payload": {"code": "banned", "reason": reason}
                    })
                await ws.close(code=4005)
            except Exception:
                pass
            self.disconnect(circle_id, ws)
        
        if to_remove:
            logger.info("Kicked %d connections for user %s from circle %s", len(to_remove), target_id, circle_id)

    async def broadcast(self, circle_id: str, payload: dict[str, Any]) -> None:
        """Send a JSON payload to all connections in a circle room."""
        dead: list[WebSocket] = []
        for ws in self.rooms.get(circle_id, []):
            try:
                await ws.send_json(payload)
            except Exception:
                logger.warning("Broadcast failed for a WS in circle %s — queuing for removal", circle_id)
                dead.append(ws)
        # Clean up dead connections
        for ws in dead:
            self.disconnect(circle_id, ws)

    async def send_to_one(self, ws: WebSocket, payload: dict[str, Any]) -> None:
        """Send a JSON payload to a single WebSocket connection."""
        try:
            await ws.send_json(payload)
        except Exception:
            logger.warning("send_to_one failed for a WS connection")


manager = ConnectionManager()
