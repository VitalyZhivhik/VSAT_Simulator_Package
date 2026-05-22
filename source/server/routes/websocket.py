import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("vsat.websocket")

router = APIRouter()

HEARTBEAT_INTERVAL = 30  # seconds


class ConnectionManager:
    def __init__(self):
        # Student connections: session_id -> set of WebSockets
        self.connections: dict[str, set[WebSocket]] = {}
        # Admin connections: set of WebSockets
        self.admin_connections: set[WebSocket] = set()

    # ── Student connections ──────────────────────────────────

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.connections:
            self.connections[session_id] = set()
        self.connections[session_id].add(websocket)
        logger.info("WS connected: session=%s (total: %d sessions)", session_id, len(self.connections))
        await self.notify_admins({
            "type": "student_connected",
            "session_id": session_id,
        })

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.connections:
            self.connections[session_id].discard(websocket)
            if not self.connections[session_id]:
                del self.connections[session_id]

    async def disconnect_and_notify(self, session_id: str, websocket: WebSocket):
        self.disconnect(session_id, websocket)
        logger.info("WS disconnected: session=%s (total: %d sessions)", session_id, len(self.connections))
        await self.notify_admins({
            "type": "student_disconnected",
            "session_id": session_id,
        })

    async def send_to_session(self, session_id: str, message: dict):
        if session_id not in self.connections:
            return
        dead: list[WebSocket] = []
        for ws in self.connections[session_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections[session_id].discard(ws)
        if session_id in self.connections and not self.connections[session_id]:
            del self.connections[session_id]

    async def broadcast_all(self, message: dict):
        for session_id in list(self.connections.keys()):
            await self.send_to_session(session_id, message)

    def get_connected_sessions(self) -> list[str]:
        return list(self.connections.keys())

    # ── Admin connections ────────────────────────────────────

    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_connections.add(websocket)

    def disconnect_admin(self, websocket: WebSocket):
        self.admin_connections.discard(websocket)

    async def notify_admins(self, message: dict):
        if not self.admin_connections:
            return
        dead: list[WebSocket] = []
        for ws in self.admin_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.admin_connections.discard(ws)


manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    # Prevent "admin" from being treated as a session_id
    if session_id == "admin":
        await admin_websocket_endpoint(websocket)
        return

    await manager.connect(session_id, websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=HEARTBEAT_INTERVAL,
                )
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await manager.disconnect_and_notify(session_id, websocket)


async def admin_websocket_endpoint(websocket: WebSocket):
    await manager.connect_admin(websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=HEARTBEAT_INTERVAL,
                )
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect_admin(websocket)
