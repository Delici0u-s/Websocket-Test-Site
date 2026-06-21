"""
A minimal WebSocket client built directly on `socket`, implementing
RFC 6455 (https://www.rfc-editor.org/rfc/rfc6455) by hand:

  - the HTTP/1.1 Upgrade handshake (section 4)
  - the binary frame format (section 5.2)
  - client-to-server masking (section 5.3, mandatory for clients)
  - text/binary/close/ping/pong opcodes

This intentionally does NOT use the `websockets` or `wsproto` packages.
The point is to show you understand what `new WebSocket(url)` (the
WHATWG browser API) is doing underneath, at the byte level.

Usage:
    python raw_client.py ws://localhost:8000/ws
"""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import struct
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"  # RFC 6455 section 1.3, fixed magic value

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA

OPCODE_NAMES = {
    OPCODE_CONTINUATION: "CONTINUATION",
    OPCODE_TEXT: "TEXT",
    OPCODE_BINARY: "BINARY",
    OPCODE_CLOSE: "CLOSE",
    OPCODE_PING: "PING",
    OPCODE_PONG: "PONG",
}


@dataclass
class Frame:
    fin: bool
    opcode: int
    payload: bytes

    def describe(self) -> str:
        return f"FIN={int(self.fin)} opcode=0x{self.opcode:X} ({OPCODE_NAMES.get(self.opcode, '?')}) len={len(self.payload)}"


class RawWebSocketClient:
    """Speaks just enough RFC 6455 to talk to a compliant server."""

    def __init__(self, url: str):
        parsed = urlparse(url)
        if parsed.scheme not in ("ws", "wss"):
            raise ValueError("only ws:// is supported by this minimal client (no TLS handling)")
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.path = parsed.path or "/"
        self.sock: socket.socket | None = None

    # ---- Handshake (RFC 6455 section 4) -----------------------------------

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port))
        key = base64.b64encode(os.urandom(16)).decode()

        request = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        print("--- HTTP handshake request ---")
        print(request)
        self.sock.sendall(request.encode())

        response = self._recv_until_double_crlf()
        print("--- HTTP handshake response ---")
        print(response.decode(errors="replace"))

        self._verify_handshake(response, key)

    def _recv_until_double_crlf(self) -> bytes:
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("socket closed during handshake")
            buf += chunk
        return buf

    def _verify_handshake(self, response: bytes, sent_key: str) -> None:
        lines = response.decode(errors="replace").split("\r\n")
        status_line = lines[0]
        if "101" not in status_line:
            raise ConnectionError(f"handshake failed: {status_line}")

        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        expected = base64.b64encode(hashlib.sha1((sent_key + GUID).encode()).digest()).decode()
        actual = headers.get("sec-websocket-accept", "")
        if actual != expected:
            raise ConnectionError(
                f"Sec-WebSocket-Accept mismatch: expected {expected!r}, got {actual!r}"
            )
        print(f"[handshake OK] Sec-WebSocket-Accept verified: {actual}")

    # ---- Framing (RFC 6455 section 5) -------------------------------------

    def send_frame(self, opcode: int, payload: bytes = b"", fin: bool = True) -> None:
        """Builds and sends a single frame. Clients MUST mask (section 5.3)."""
        first_byte = (0x80 if fin else 0x00) | opcode
        mask_key = os.urandom(4)
        masked_payload = self._apply_mask(payload, mask_key)

        length = len(payload)
        if length <= 125:
            header = struct.pack("!BB", first_byte, 0x80 | length)
        elif length <= 0xFFFF:
            header = struct.pack("!BBH", first_byte, 0x80 | 126, length)
        else:
            header = struct.pack("!BBQ", first_byte, 0x80 | 127, length)

        frame = header + mask_key + masked_payload
        self.sock.sendall(frame)
        print(f"[sent]     {Frame(fin, opcode, payload).describe()}")

    @staticmethod
    def _apply_mask(data: bytes, mask_key: bytes) -> bytes:
        # RFC 6455 5.3: byte i of output = byte i of input XOR mask[i % 4]
        return bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))

    def recv_frame(self) -> Frame:
        """Reads exactly one frame from the server. Server frames are unmasked."""
        header = self._recv_exact(2)
        first_byte, second_byte = header[0], header[1]

        fin = bool(first_byte & 0x80)
        opcode = first_byte & 0x0F
        masked = bool(second_byte & 0x80)  # servers MUST NOT mask; should be 0
        length = second_byte & 0x7F

        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]

        mask_key = self._recv_exact(4) if masked else None
        payload = self._recv_exact(length)
        if mask_key:
            payload = self._apply_mask(payload, mask_key)

        frame = Frame(fin, opcode, payload)
        print(f"[received] {frame.describe()}")
        return frame

    def _recv_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("socket closed unexpectedly")
            buf += chunk
        return buf

    def close(self, code: int = 1000, reason: str = "") -> None:
        payload = struct.pack("!H", code) + reason.encode()
        self.send_frame(OPCODE_CLOSE, payload)
        self.sock.close()


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8000/ws"
    client = RawWebSocketClient(url)
    client.connect()

    # Server should send a TEXT welcome frame first (see backend /ws handler)
    client.recv_frame()

    client.send_frame(OPCODE_TEXT, b'{"type": "ping"}')
    client.recv_frame()

    client.send_frame(OPCODE_PING, b"are you alive?")
    client.recv_frame()  # expect PONG echoing the same payload

    client.close()
    print("[closed] connection terminated cleanly")


if __name__ == "__main__":
    main()
