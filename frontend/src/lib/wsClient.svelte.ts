/**
 * Thin wrapper around the browser's native WebSocket
 * (https://websockets.spec.whatwg.org/#the-websocket-interface).
 *
 * This deliberately stays close to the spec's interface rather than
 * hiding it: readyState, the four events (open/message/error/close),
 * and the close code/reason are all surfaced to the UI so you can show
 * the actual state machine during a demo.
 *
 * Spec state values (readyState):
 *   0 CONNECTING, 1 OPEN, 2 CLOSING, 3 CLOSED
 */

export type ReadyState = 0 | 1 | 2 | 3;

export const READY_STATE_NAMES: Record<ReadyState, string> = {
	0: 'CONNECTING',
	1: 'OPEN',
	2: 'CLOSING',
	3: 'CLOSED'
};

export interface LogEntry {
	ts: number;
	direction: 'sent' | 'received' | 'event';
	summary: string;
	raw?: string;
}

export class WSClient {
	socket: WebSocket | null = null;
	readyState: ReadyState = $state(3);
	log: LogEntry[] = $state([]);
	lastCloseCode: number | null = $state(null);
	lastCloseReason: string = $state('');

	private url: string;

	constructor(url: string) {
		this.url = url;
	}

	private pushLog(direction: LogEntry['direction'], summary: string, raw?: string) {
		this.log = [...this.log, { ts: Date.now(), direction, summary, raw }];
	}

	connect(): void {
		if (this.socket && this.readyState !== 3) {
			return; // already connecting/open
		}

		this.socket = new WebSocket(this.url);
		this.readyState = this.socket.readyState as ReadyState;

		this.socket.addEventListener('open', () => {
			this.readyState = 1;
			this.pushLog('event', 'open - handshake complete, connection is OPEN');
		});

		this.socket.addEventListener('message', (event: MessageEvent) => {
			this.pushLog('received', `message (${typeof event.data})`, String(event.data));
		});

		this.socket.addEventListener('error', () => {
			this.pushLog('event', 'error event fired');
		});

		this.socket.addEventListener('close', (event: CloseEvent) => {
			this.readyState = 3;
			this.lastCloseCode = event.code;
			this.lastCloseReason = event.reason;
			this.pushLog(
				'event',
				`close - code=${event.code} clean=${event.wasClean} reason="${event.reason}"`
			);
		});
	}

	send(payload: unknown): void {
		if (!this.socket || this.readyState !== 1) {
			this.pushLog('event', 'send() called but socket is not OPEN - dropped');
			return;
		}
		const text = typeof payload === 'string' ? payload : JSON.stringify(payload);
		this.socket.send(text);
		this.pushLog('sent', 'text frame', text);
	}

	close(code = 1000, reason = ''): void {
		if (!this.socket) return;
		this.readyState = 2;
		this.socket.close(code, reason);
	}

	clearLog(): void {
		this.log = [];
	}
}
