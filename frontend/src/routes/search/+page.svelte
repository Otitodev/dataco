<script lang="ts">
	import { searchAssets, type AssetMeta } from '$lib/api';
	import Card from '$lib/components/Card.svelte';

	let query = $state('');
	let results = $state<AssetMeta[]>([]);
	let searching = $state(false);
	let searched = $state(false);

	async function doSearch() {
		if (!query.trim()) return;
		searching = true;
		try {
			results = await searchAssets(query);
		} finally {
			searching = false;
			searched = true;
		}
	}
</script>

<svelte:head>
	<title>Search · Dataco</title>
</svelte:head>

<h1 class="mb-8 text-3xl font-semibold tracking-tight">Search assets</h1>

<form
	onsubmit={(e) => {
		e.preventDefault();
		doSearch();
	}}
	class="mb-6 flex gap-2.5"
>
	<input
		type="text"
		bind:value={query}
		placeholder="Dataset, KPI, table, or business term…"
		class="flex-1 rounded-full border border-line bg-surface-card px-5 py-2.5 text-[15px] text-ink-900 placeholder:text-ink-400 focus:border-brand focus:outline-none"
	/>
	<button
		type="submit"
		class="rounded-full bg-brand px-5 py-2.5 text-[15px] font-medium text-white transition-colors hover:bg-brand-ink disabled:opacity-40"
		disabled={searching}
	>
		{searching ? 'Searching…' : 'Search'}
	</button>
</form>

{#if results.length > 0}
	<div class="space-y-3">
		{#each results as asset}
			<Card class="p-5">
				<h2 class="text-[15px] font-semibold tracking-tight text-ink-900">{asset.name}</h2>
				<p class="mt-1 text-sm text-ink-600">{asset.description || 'No description'}</p>
				<p class="mt-2 text-xs text-ink-400">Owner: {asset.owner ?? 'Unassigned'}</p>
			</Card>
		{/each}
	</div>
{:else if searched && !searching}
	<p class="text-[15px] text-ink-400">
		No assets match “{query}”. Try a dataset, table, or business term.
	</p>
{/if}
