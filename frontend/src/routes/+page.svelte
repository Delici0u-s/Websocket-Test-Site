<script lang="ts">
	import { WSClient, READY_STATE_NAMES } from '$lib/wsClient.svelte';
	import { resolveWsUrl } from '$lib/config';

	let wsUrl = $state(resolveWsUrl());
	let client = $state<WSClient | null>(null);
	let messageText = $state('');

	function connect() {
		client = new WSClient(wsUrl);
		client.connect();
	}

	function disconnect() {
		client?.close(1000, 'user closed');
	}

	function sendMessage() {
		if (!messageText.trim()) return;
		client?.send({ type: 'message', text: messageText });
		messageText = '';
	}

	function sendPing() {
		client?.send({ type: 'ping' });
	}
</script>

<svelte:head>
	<title>WebSocket Protocol Demo</title>
</svelte:head>

<main>
	<h1>WebSocket Protocol Demo</h1>
	<p class="subtitle">
		Browser <code>WebSocket</code> interface against a FastAPI backend.
		See <code>protocol-tools/raw_client.py</code> for the hand-rolled RFC&nbsp;6455 client.
	</p>

	<section class="connection">
		<label>
			Server URL
			<input bind:value={wsUrl} disabled={client !== null && client.readyState !== 3} />
		</label>
		<div class="buttons">
			<button onclick={connect} disabled={client !== null && client.readyState !== 3}>
				Connect
			</button>
			<button onclick={disconnect} disabled={!client || client.readyState !== 1}>
				Disconnect
			</button>
		</div>

		{#if client}
			<p class="state">
				readyState:
				<strong class="badge state-{client.readyState}">
					{client.readyState} - {READY_STATE_NAMES[client.readyState]}
				</strong>
				{#if client.lastCloseCode !== null}
					<span class="close-info">
						(last close code {client.lastCloseCode}{client.lastCloseReason
							? `: ${client.lastCloseReason}`
							: ''})
					</span>
				{/if}
			</p>
		{/if}
	</section>

	<section class="messaging">
		<input
			bind:value={messageText}
			placeholder="Message text"
			disabled={!client || client.readyState !== 1}
			onkeydown={(e) => e.key === 'Enter' && sendMessage()}
		/>
		<button onclick={sendMessage} disabled={!client || client.readyState !== 1}>Send</button>
		<button onclick={sendPing} disabled={!client || client.readyState !== 1}>Send ping</button>
	</section>

	<section class="log">
		<h2>Frame / event log</h2>
		{#if client && client.log.length > 0}
			<ol>
				{#each client.log as entry (entry.ts + entry.summary)}
					<li class="entry {entry.direction}">
						<span class="ts">{new Date(entry.ts).toLocaleTimeString()}</span>
						<span class="direction">{entry.direction}</span>
						<span class="summary">{entry.summary}</span>
						{#if entry.raw}
							<pre class="raw">{entry.raw}</pre>
						{/if}
					</li>
				{/each}
			</ol>
		{:else}
			<p class="empty">No activity yet. Connect to start.</p>
		{/if}
	</section>
</main>

<style>
	main {
		max-width: 720px;
		margin: 2rem auto;
		padding: 0 1rem;
		font-family: system-ui, sans-serif;
		color: #1a1a1a;
	}
	h1 {
		font-size: 1.5rem;
		margin-bottom: 0.25rem;
	}
	.subtitle {
		color: #555;
		font-size: 0.9rem;
		margin-bottom: 1.5rem;
	}
	code {
		background: #f1f1f1;
		padding: 0.1rem 0.3rem;
		border-radius: 3px;
		font-size: 0.85em;
	}
	section {
		margin-bottom: 1.5rem;
		padding: 1rem;
		border: 1px solid #ddd;
		border-radius: 6px;
	}
	label {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		font-size: 0.85rem;
		margin-bottom: 0.75rem;
	}
	input {
		padding: 0.5rem;
		border: 1px solid #ccc;
		border-radius: 4px;
		font-size: 0.9rem;
	}
	.connection input {
		width: 100%;
	}
	.messaging {
		display: flex;
		gap: 0.5rem;
	}
	.messaging input {
		flex: 1;
	}
	.buttons {
		display: flex;
		gap: 0.5rem;
	}
	button {
		padding: 0.5rem 1rem;
		border: 1px solid #888;
		border-radius: 4px;
		background: #fafafa;
		cursor: pointer;
		font-size: 0.9rem;
	}
	button:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.state {
		font-size: 0.85rem;
		margin-top: 0.75rem;
	}
	.badge {
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		font-family: monospace;
	}
	.state-0 {
		background: #fff3cd;
	}
	.state-1 {
		background: #d4edda;
	}
	.state-2 {
		background: #fde2c0;
	}
	.state-3 {
		background: #f8d7da;
	}
	.close-info {
		color: #777;
		font-size: 0.8rem;
	}
	.log h2 {
		font-size: 1rem;
		margin-top: 0;
	}
	.log ol {
		list-style: none;
		padding: 0;
		margin: 0;
		max-height: 320px;
		overflow-y: auto;
	}
	.entry {
		padding: 0.4rem 0;
		border-bottom: 1px solid #eee;
		font-size: 0.85rem;
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		align-items: baseline;
	}
	.ts {
		color: #999;
		font-family: monospace;
		font-size: 0.75rem;
	}
	.direction {
		font-weight: 600;
		text-transform: uppercase;
		font-size: 0.7rem;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
	}
	.entry.sent .direction {
		background: #d4edda;
	}
	.entry.received .direction {
		background: #d6e4f0;
	}
	.entry.event .direction {
		background: #eee;
	}
	.raw {
		flex-basis: 100%;
		margin: 0.25rem 0 0 0;
		background: #f7f7f7;
		padding: 0.4rem;
		border-radius: 4px;
		font-size: 0.8rem;
		overflow-x: auto;
	}
	.empty {
		color: #888;
		font-size: 0.85rem;
	}
</style>
