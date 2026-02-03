import asyncio
import json
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket

LOG = logging.getLogger("websocket")


class ConnectionManager:
    """Manages WebSocket connections for real-time sensor data broadcasting."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.device_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, device_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if device_id:
            if device_id not in self.device_subscriptions:
                self.device_subscriptions[device_id] = set()
            self.device_subscriptions[device_id].add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        for device_id in list(self.device_subscriptions.keys()):
            self.device_subscriptions[device_id].discard(websocket)
            if not self.device_subscriptions[device_id]:
                del self.device_subscriptions[device_id]

    def subscribe_to_device(self, websocket: WebSocket, device_id: str):
        """Subscribe a WebSocket to a specific device's updates."""
        if device_id not in self.device_subscriptions:
            self.device_subscriptions[device_id] = set()
        self.device_subscriptions[device_id].add(websocket)

    def unsubscribe_from_device(self, websocket: WebSocket, device_id: str):
        """Unsubscribe a WebSocket from a device's updates."""
        if device_id in self.device_subscriptions:
            self.device_subscriptions[device_id].discard(websocket)
            if not self.device_subscriptions[device_id]:
                del self.device_subscriptions[device_id]

    async def broadcast_sensor_update(self, device_id: str, sensor_type: str, data: dict):
        """Broadcast a sensor update to all relevant clients."""
        message = {
            "type": "sensor_update",
            "device_id": device_id,
            "sensor_type": sensor_type,
            "data": data
        }
        
        subscribers = self.device_subscriptions.get(device_id, set())
        if not subscribers and not self.active_connections:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = []
        
        # Send to device-specific subscribers
        for ws in list(subscribers):
            try:
                await asyncio.wait_for(ws.send_text(message_json), timeout=1.0)
            except Exception:
                disconnected.append(ws)
        
        # Send to global listeners (not subscribed to any device)
        global_listeners = self.active_connections - set().union(
            *self.device_subscriptions.values()
        ) if self.device_subscriptions else self.active_connections
        
        for ws in list(global_listeners):
            try:
                await asyncio.wait_for(ws.send_text(message_json), timeout=1.0)
            except Exception:
                disconnected.append(ws)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)


# Global connection manager instance
manager = ConnectionManager()
