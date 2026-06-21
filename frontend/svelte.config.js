import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		// adapter-node: produces a standalone Node server (build/index.js),
		// which we run directly in the Docker image. This is the simplest
		// adapter to containerize - no platform-specific glue needed.
		adapter: adapter()
	}
};

export default config;
