<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		href,
		class: klass = '',
		children
	}: {
		href?: string;
		class?: string;
		children: Snippet;
	} = $props();
</script>

{#if href}
	<a
		{href}
		class="block rounded-2xl border border-line bg-surface-card transition-all duration-200 hover:border-transparent hover:shadow-[0_6px_20px_rgba(0,0,0,0.08)] {klass}"
	>
		{@render children()}
	</a>
{:else}
	<div class="rounded-2xl border border-line bg-surface-card {klass}">
		{@render children()}
	</div>
{/if}
