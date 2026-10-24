import asyncio
import json
import logging
from typing import Dict, List, Set, Any
from fastapi import WebSocket

logger = logging.getLogger("websocket_manager")

class ConnectionManager:
    """
    Manages active WebSocket connections per session_id and globally.
    Enables low-latency streaming of ReAct thought chains, tool executions,
    and partial report synthesis to connected frontend clients.
    """
    def __init__(self):
        # Maps session_id to set of active WebSockets
        self.active_sessions: Dict[str, Set[WebSocket]] = {}
        # Global listeners (e.g. admin monitoring or activity dashboard)
        self.global_listeners: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        async with self._lock:
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = set()
            self.active_sessions[session_id].add(websocket)
            logger.info(f"WebSocket client connected to session: {session_id} (active: {len(self.active_sessions[session_id])})")

    async def connect_global(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.global_listeners.add(websocket)
            logger.info(f"Global WebSocket client connected (active: {len(self.global_listeners)})")

    async def disconnect(self, websocket: WebSocket, session_id: str):
        async with self._lock:
            if session_id in self.active_sessions:
                self.active_sessions[session_id].discard(websocket)
                if not self.active_sessions[session_id]:
                    del self.active_sessions[session_id]
            self.global_listeners.discard(websocket)
            logger.info(f"WebSocket client disconnected from session: {session_id}")

    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """
        Broadcasts message to all clients subscribed to a given session_id.
        """
        payload = json.dumps(message, default=str)
        async with self._lock:
            sockets = list(self.active_sessions.get(session_id, []))
            globals_ = list(self.global_listeners)

        all_recipients = set(sockets + globals_)
        dead_sockets = []

        for ws in all_recipients:
            try:
                await ws.send_text(payload)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for dead_ws in dead_sockets:
                    if session_id in self.active_sessions:
                        self.active_sessions[session_id].discard(dead_ws)
                    self.global_listeners.discard(dead_ws)

ws_manager = ConnectionManager()
