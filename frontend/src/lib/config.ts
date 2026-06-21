/**
 * Resolves the backend WebSocket URL at runtime.
 *
 * PUBLIC_WS_URL is injected at build time via SvelteKit's $env/static/public
 * (must be prefixed PUBLIC_ to be exposed to the browser bundle).
 * Falls back to deriving ws(s)://<current-host>/ws so the same build works
 * both on localhost and behind a reverse proxy without rebuilding.
 */
import { PUBLIC_WS_URL } from '$env/static/public';

export function resolveWsUrl(): string {
	if (PUBLIC_WS_URL) return PUBLIC_WS_URL;

	if (typeof window === 'undefined') return '';
	const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
	return `${protocol}//${window.location.host}/ws`;
}
