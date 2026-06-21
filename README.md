# WebSocket Protocol Demo

A FastAPI + SvelteKit project for studying and demonstrating the WebSocket
protocol (RFC 6455) at three levels:

1. **Browser API level** - `frontend/`, using the native
   [`WebSocket` interface](https://websockets.spec.whatwg.org/#the-websocket-interface).
2. **Application server level** - `backend/`, FastAPI's WebSocket support
   (built on Starlette + the `websockets` package).
3. **Wire protocol level** - `protocol-tools/raw_client.py`, a client built
   directly on `socket` that performs the HTTP Upgrade handshake and frame
   (de)masking by hand, per [RFC 6455](https://www.rfc-editor.org/rfc/rfc6455).

Use (1) and (2) to build/demo the actual feature. Use (3) when you need to
show you understand what's happening under the hood for the protocol part
of the course.

## Repo layout

```
.
├── backend/            FastAPI app (/ws, /ws/debug, /health)
├── frontend/            SvelteKit app (native WebSocket client + frame log UI)
├── protocol-tools/      Raw-socket RFC 6455 client + tshark capture helper
├── nginx/               Reverse proxy config (single origin, WS upgrade headers)
├── docker-compose.yml   Full local/deployable stack
└── docs/                Notes for write-up (handshake, framing, deploy access)
```

## Running locally (without Docker)

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173.

## Running the raw protocol client

With the backend running on port 8000:
```bash
cd protocol-tools
python raw_client.py ws://localhost:8000/ws
```
This prints the handshake request/response and every frame it sends/receives,
including FIN bit, opcode, and payload length - useful to screenshot or paste
directly into your report next to the RFC text.

## Running everything via Docker Compose

```bash
docker compose up --build
```
- Frontend directly: http://localhost:3000
- Backend directly: http://localhost:8000
- Through the single-origin Nginx proxy (closest to a real deployment): http://localhost:8080

## Capturing packets for the write-up

```bash
cd protocol-tools
python handshake_capture.py --iface lo --port 8000 --out capture.pcapng
# in another terminal:
python raw_client.py ws://localhost:8000/ws
```
Then open `capture.pcapng` in Wireshark, filter on
`websocket || (http.upgrade == "websocket")`.

## Deployment / access model

See [`docs/deployment-access.md`](docs/deployment-access.md) for how this is
deployed without giving teammates access to the underlying server.
