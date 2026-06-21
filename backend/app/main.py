"""
FastAPI WebSocket backend.

Two endpoints on purpose:
  /ws       - normal echo/broadcast endpoint, used by the SvelteKit frontend
  /ws/debug - same logic, but logs handshake headers + frame metadata to
              stdout so you can show *what actually happened on the wire*
              during a demo, without needing Wireshark every time.

Starlette (which FastAPI sits on top of) negotiates the handshake and
frame parsing for you via the `websockets` or `wsproto` package. That's
fine for the *application* - but for the protocol part of your course
deliverable, pair this with protocol-tools/raw_client.py and
protocol-tools/handshake_capture.py, which do NOT use any WebSocket
library and instead speak RFC 6455 directly over a raw socket.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ws-backend")

app = FastAPI(title="WebSocket Protocol Demo")

# Dev-friendly CORS. Tighten origins for the deployed version (see .env / compose).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class ConnectionRegistry:
    """Tracks active connections so we can broadcast and report stats."""

    active: dict[int, WebSocket] = field(default_factory=dict)
    _next_id: int = 0

    def add(self, ws: WebSocket) -> int:
        conn_id = self._next_id
        self._next_id += 1
        self.active[conn_id] = ws
        return conn_id

    def remove(self, conn_id: int) -> None:
        self.active.pop(conn_id, None)

    async def broadcast(self, message: dict, exclude: int | None = None) -> None:
        dead: list[int] = []
        for conn_id, ws in self.active.items():
            if conn_id == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:  # connection died mid-broadcast
                dead.append(conn_id)
        for conn_id in dead:
            self.remove(conn_id)


registry = ConnectionRegistry()


@app.get("/health")
async def health():
    return {"status": "ok", "active_connections": len(registry.active)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Application-facing endpoint. Plain JSON text frames:
        {"type": "message", "text": "..."}
        {"type": "ping"} -> server replies {"type": "pong", "ts": ...}
    """
    await websocket.accept()
    conn_id = registry.add(websocket)
    log.info(f"client {conn_id} connected ({len(registry.active)} total)")

    try:
        await websocket.send_json({"type": "welcome", "conn_id": conn_id})

        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "invalid JSON"})
                continue

            msg_type = payload.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "ts": time.time()})
            elif msg_type == "message":
                await registry.broadcast(
                    {"type": "message", "from": conn_id, "text": payload.get("text", "")},
                    exclude=None,  # echo to everyone including sender, simplest for a demo
                )
            else:
                await websocket.send_json({"type": "error", "detail": f"unknown type '{msg_type}'"})

    except WebSocketDisconnect as exc:
        log.info(f"client {conn_id} disconnected, code={exc.code}")
    finally:
        registry.remove(conn_id)


@app.websocket("/ws/debug")
async def websocket_debug_endpoint(websocket: WebSocket):
    """
    Same behaviour as /ws, but logs handshake headers and basic frame
    metadata on every receive. Use this one while screen-recording or
    presenting, so you can point at real log lines next to the spec text.
    """
    headers = dict(websocket.headers)
    log.info("--- WebSocket handshake (debug) ---")
    for key in ("upgrade", "connection", "sec-websocket-key", "sec-websocket-version", "sec-websocket-extensions"):
        if key in headers:
            log.info(f"  {key}: {headers[key]}")

    await websocket.accept()
    conn_id = registry.add(websocket)

    try:
        while True:
            message = await websocket.receive()
            # Starlette gives us the decoded message dict; the raw frame
            # bytes are already consumed by this point. This still lets us
            # show opcode-equivalent info (text vs bytes vs disconnect).
            if "text" in message:
                log.info(f"  recv TEXT frame, {len(message['text'])} bytes payload")
                await websocket.send_text(message["text"])
            elif "bytes" in message:
                log.info(f"  recv BINARY frame, {len(message['bytes'])} bytes payload")
                await websocket.send_bytes(message["bytes"])
            elif message.get("type") == "websocket.disconnect":
                log.info(f"  recv CLOSE, code={message.get('code')}")
                break
    finally:
        registry.remove(conn_id)
