#!/usr/bin/env python3
"""
Optional helper: captures the WebSocket handshake + first few frames using
tshark (Wireshark's CLI), so you have a packet-level artifact to attach to
your protocol writeup alongside raw_client.py's manual implementation.

This is OS-independent as long as Wireshark/tshark is installed and the
user has packet-capture permissions (on Linux: be in the `wireshark`
group, or run with sudo).

Usage:
    python handshake_capture.py --iface lo --port 8000 --out capture.pcapng
    # in another terminal, while this is running:
    python raw_client.py ws://localhost:8000/ws

Then open capture.pcapng in Wireshark and filter on:
    websocket || (http.upgrade == "websocket")
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iface", default="lo", help="capture interface (default: lo / loopback)")
    parser.add_argument("--port", type=int, default=8000, help="server port to filter on")
    parser.add_argument("--out", default="capture.pcapng", help="output pcapng file")
    parser.add_argument("--duration", type=int, default=30, help="capture duration in seconds")
    args = parser.parse_args()

    if shutil.which("tshark") is None:
        print(
            "tshark not found. Install Wireshark (includes tshark):\n"
            "  Fedora: sudo dnf install wireshark-cli\n"
            "  Ubuntu/Debian: sudo apt install tshark\n",
            file=sys.stderr,
        )
        return 1

    cmd = [
        "tshark",
        "-i", args.iface,
        "-f", f"tcp port {args.port}",
        "-a", f"duration:{args.duration}",
        "-w", args.out,
    ]
    print(f"Capturing on {args.iface}, port {args.port}, for {args.duration}s -> {args.out}")
    print("Run your client/connection now in another terminal.")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

    print(f"\nDone. Open with: wireshark {args.out}")
    print('Suggested display filter: websocket || (http.upgrade == "websocket")')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
