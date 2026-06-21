"""
End-to-end test script for the /ws endpoint. Works against either:
  - local dev:    ws://localhost:8000/ws
  - deployed Pi:  wss://ws-demo.se-dy.de/ws   (or whatever your domain is)

Uses the `websockets` library (not the raw protocol client) because this
is testing *application behaviour*, not the wire format - use
raw_client.py separately if you need to demonstrate the protocol itself.

Usage:
    pip install websockets
    python test_ws.py                                  # defaults to localhost
    python test_ws.py ws://localhost:8000/ws
    python test_ws.py wss://ws-demo.se-dy.de/ws

Exit code 0 = all checks passed, 1 = something failed.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time

import websockets
from websockets.exceptions import ConnectionClosed

DEFAULT_URL = "ws://localhost:8000/ws"


class TestFailure(Exception):
    pass


async def expect_json(ws, expected_type: str, timeout: float = 5.0) -> dict:
    """Receive one message, parse as JSON, assert its 'type' field."""
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    data = json.loads(raw)
    if data.get("type") != expected_type:
        raise TestFailure(f"expected type='{expected_type}', got: {data}")
    return data


async def test_connect_and_welcome(url: str) -> None:
    """Server should accept the connection and immediately send a welcome frame."""
    async with websockets.connect(url) as ws:
        msg = await expect_json(ws, "welcome")
        assert "conn_id" in msg, "welcome message missing conn_id"
    print("[PASS] connect + welcome message")


async def test_ping_pong(url: str) -> None:
    """Application-level ping (JSON message), not the WS protocol ping frame."""
    async with websockets.connect(url) as ws:
        await expect_json(ws, "welcome")

        await ws.send(json.dumps({"type": "ping"}))
        msg = await expect_json(ws, "pong")
        assert "ts" in msg, "pong missing timestamp"

        latency_ms = (time.time() - msg["ts"]) * 1000
        print(f"[PASS] app-level ping/pong (round trip ~{latency_ms:.1f} ms)")


async def test_echo_broadcast(url: str) -> None:
    """A sent message should come back to the sender (current /ws behaviour)."""
    async with websockets.connect(url) as ws:
        await expect_json(ws, "welcome")

        test_text = "hello from test_ws.py"
        await ws.send(json.dumps({"type": "message", "text": test_text}))
        msg = await expect_json(ws, "message")
        assert msg["text"] == test_text, f"echo mismatch: {msg}"
    print("[PASS] message echo/broadcast")


async def test_invalid_json_returns_error(url: str) -> None:
    """Malformed input should produce a graceful error, not a dropped connection."""
    async with websockets.connect(url) as ws:
        await expect_json(ws, "welcome")

        await ws.send("not valid json{{{")
        msg = await expect_json(ws, "error")
        assert "detail" in msg
    print("[PASS] invalid JSON handled gracefully")


async def test_unknown_message_type(url: str) -> None:
    """Unrecognised 'type' field should also produce a structured error."""
    async with websockets.connect(url) as ws:
        await expect_json(ws, "welcome")

        await ws.send(json.dumps({"type": "not_a_real_type"}))
        msg = await expect_json(ws, "error")
        assert "unknown type" in msg["detail"]
    print("[PASS] unknown message type handled gracefully")


async def test_two_clients_see_each_others_messages(url: str) -> None:
    """Broadcast should reach a second, independently connected client."""
    async with websockets.connect(url) as ws_a, websockets.connect(url) as ws_b:
        await expect_json(ws_a, "welcome")
        await expect_json(ws_b, "welcome")

        await ws_a.send(json.dumps({"type": "message", "text": "from A"}))

        msg_on_a = await expect_json(ws_a, "message")
        msg_on_b = await expect_json(ws_b, "message")
        assert msg_on_a["text"] == "from A"
        assert msg_on_b["text"] == "from A"
    print("[PASS] broadcast reaches a second client")


async def test_clean_close(url: str) -> None:
    """Closing with code 1000 should be reported as wasClean / no error."""
    ws = await websockets.connect(url)
    await expect_json(ws, "welcome")
    await ws.close(code=1000, reason="test done")
    assert ws.close_code == 1000, f"expected close code 1000, got {ws.close_code}"
    print("[PASS] clean close (code 1000)")


TESTS = [
    test_connect_and_welcome,
    test_ping_pong,
    test_echo_broadcast,
    test_invalid_json_returns_error,
    test_unknown_message_type,
    test_two_clients_see_each_others_messages,
    test_clean_close,
]


async def run_all(url: str) -> bool:
    print(f"Target: {url}\n")
    failures = []
    for test in TESTS:
        try:
            await test(url)
        except (TestFailure, AssertionError) as exc:
            print(f"[FAIL] {test.__name__}: {exc}")
            failures.append(test.__name__)
        except (ConnectionClosed, OSError, asyncio.TimeoutError) as exc:
            print(f"[FAIL] {test.__name__}: connection problem - {exc}")
            failures.append(test.__name__)

    print()
    if failures:
        print(f"{len(failures)}/{len(TESTS)} tests failed: {', '.join(failures)}")
        return False
    print(f"all {len(TESTS)} tests passed")
    return True


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    ok = asyncio.run(run_all(url))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
