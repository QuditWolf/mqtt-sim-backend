import asyncio
import json
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect

LOG = logging.getLogger("websocket")


class ConnectionManager:
    """Manages WebSocket connections for real-time sensor data broadcasting."""

    def __init__(self):
        # All active connections
        self.active_connections: Set[WebSocket] = set()
        # Device-specific subscriptions: device_id -> set of websockets
        self.device_subscriptions: Dict[str, Set[WebSocket]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, device_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
            if device_id:
                if device_id not in self.device_subscriptions:
                    self.device_subscriptions[device_id] = set()
                self.device_subscriptions[device_id].add(websocket)
        LOG.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
            # Remove from all device subscriptions
            for device_id in list(self.device_subscriptions.keys()):
                self.device_subscriptions[device_id].discard(websocket)
                if not self.device_subscriptions[device_id]:
                    del self.device_subscriptions[device_id]
        LOG.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def subscribe_to_device(self, websocket: WebSocket, device_id: str):
        """Subscribe a WebSocket to a specific device's updates."""
        async with self._lock:
            if device_id not in self.device_subscriptions:
                self.device_subscriptions[device_id] = set()
            self.device_subscriptions[device_id].add(websocket)

    async def unsubscribe_from_device(self, websocket: WebSocket, device_id: str):
        """Unsubscribe a WebSocket from a device's updates."""
        async with self._lock:
            if device_id in self.device_subscriptions:
                self.device_subscriptions[device_id].discard(websocket)

    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = set()
        
        for websocket in self.active_connections:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                LOG.warning(f"Failed to send to websocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_to_device(self, device_id: str, message: dict):
        """Broadcast a message to clients subscribed to a specific device."""
        subscribers = self.device_subscriptions.get(device_id, set())
        if not subscribers:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = set()
        
        for websocket in subscribers:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                LOG.warning(f"Failed to send to websocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_sensor_update(self, device_id: str, sensor_type: str, data: dict):
        """Broadcast a sensor update to all relevant clients."""
        message = {
            "type": "sensor_update",
            "device_id": device_id,
            "sensor_type": sensor_type,
            "data": data
        }
        
        # Send to device-specific subscribers
        await self.broadcast_to_device(device_id, message)
        
        # Also send to clients not subscribed to any specific device (global listeners)
        global_listeners = self.active_connections - set().union(
            *self.device_subscriptions.values()
        ) if self.device_subscriptions else self.active_connections
        
        if global_listeners:
            message_json = json.dumps(message, default=str)
            for ws in global_listeners:
                try:
                    await ws.send_text(message_json)
                except Exception:
                    pass


# Global connection manager instance
manager = ConnectionManager()
