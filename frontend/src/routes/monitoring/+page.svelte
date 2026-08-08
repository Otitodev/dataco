<script lang="ts">
	import {
		findAssets,
		getMonitored,
		addMonitored,
		removeMonitored,
		type MonitoredAsset,
		type SearchHit
	} from '$lib/api';
	import Card from '$lib/components/Card.svelte';

	let monitored = $state<MonitoredAsset[]>([]);
	let loading = $state(true);

	let query = $state('');
	let results = $state<SearchHit[]>([]);
	let searching = $state(false);
	let searched = $state(false);

	let busy = $state<Set<string>>(new Set());

	$effect(() => {
		refresh();
	});

	function refresh() {
		getMonitored()
			.then((m) => (monitored = m))
			.catch(() => (monitored = []))
			.finally(() => (loading = false));
	}

	const monitoredUrns = $derived(new Set(monitored.map((m) => m.urn)));

	async function doSearch() {
		if (!query.trim()) return;
		searching = true;
		try {
			results = await findAssets(query);
		} finally {
			searching = false;
			searched = true;
		}
	}

	async function add(urn: string) {
		busy = new Set(busy).add(urn);
		try {
			await addMonitored(urn);
			refresh();
		} finally {
			const next = new Set(busy);
			next.delete(urn);
			busy = next;
		}
	}

	async function remove(urn: string) {
		busy = new Set(busy).add(urn);
		try {
			await removeMonitored(urn);
			refresh();
		} finally {
			const next = new Set(busy);
			next.delete(urn);
			busy = next;
		}
	}

	function ago(iso: string | null): string {
		if (!iso) return 'never';
		const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
		if (s < 60) return `${s}s ago`;
		if (s < 3600) return `${Math.round(s / 60)}m ago`;
		if (s < 86400) return `${Math.round(s / 3600)}h ago`;
		return `${Math.round(s / 86400)}d ago`;
	}
</script>

<svelte:head>
	<title>Monitoring · Dataco</title>
</svelte:head>

<header class="mb-8">
	<h1 class="text-3xl font-semibold tracking-tight">Monitoring</h1>
	<p class="mt-1.5 text-[15px] text-ink-600">
		The assets Dataco watches. Add one to start tracking its trust — schema, freshness, and
		ownership. New assets are baselined at their current state, so only future changes alert.
	</p>
</header>

<!-- Add an asset -->
<section class="mb-10">
	<h2 class="mb-3 text-sm font-medium text-ink-600">Add an asset</h2>
	<form
		onsubmit={(e) => {
			e.preventDefault();
			doSearch();
		}}
		class="mb-4 flex gap-2.5"
	>
		<input
			type="text"
			bind:value={query}
			placeholder="Search your catalog — dataset, table, or business term…"
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
		<div class="space-y-2.5">
			{#each results as hit (hit.urn)}
				{@const already = monitoredUrns.has(hit.urn)}
				<Card class="flex items-center justify-between gap-4 p-4">
					<div class="min-w-0">
						<p class="truncate text-[15px] font-semibold tracking-tight text-ink-900">
							{hit.name}
						</p>
						<p class="mt-0.5 truncate text-xs text-ink-400">
							Owner: {hit.owner ?? 'Unassigned'}
						</p>
					</div>
					<button
						onclick={() => add(hit.urn)}
						disabled={already || busy.has(hit.urn)}
						class="shrink-0 rounded-full border border-line px-4 py-1.5 text-sm font-medium text-ink-900 transition-colors hover:bg-surface-sunken disabled:opacity-45"
					>
						{already ? 'Monitoring' : busy.has(hit.urn) ? 'Adding…' : 'Add'}
					</button>
				</Card>
			{/each}
		</div>
	{:else if searched && !searching}
		<p class="text-[15px] text-ink-400">No assets match “{query}”.</p>
	{/if}
</section>

<!-- Currently monitored -->
<section>
	<h2 class="mb-3 text-sm font-medium text-ink-600">
		Currently monitoring{#if !loading}
			· {monitored.length}{/if}
	</h2>

	{#if loading}
		<div class="space-y-2.5">
			{#each Array(3) as _, i (i)}
				<div class="h-16 animate-pulse rounded-2xl border border-line bg-surface-card"></div>
			{/each}
		</div>
	{:else if monitored.length === 0}
		<div class="rounded-2xl border border-line bg-surface-card px-8 py-12 text-center">
			<h3 class="text-lg font-semibold">Nothing watched yet</h3>
			<p class="mx-auto mt-2 max-w-md text-[15px] text-ink-600">
				Search above and add your critical datasets. Dataco will scan them for trust issues and
				write findings back to DataHub.
			</p>
		</div>
	{:else}
		<div class="space-y-2.5">
			{#each monitored as asset (asset.urn)}
				<Card class="flex items-center justify-between gap-4 p-4">
					<div class="min-w-0">
						<div class="flex items-center gap-2.5">
							<p class="truncate text-[15px] font-semibold tracking-tight text-ink-900">
								{asset.name}
							</p>
							{#if asset.active_issue}
								<span
									class="shrink-0 rounded-full bg-severity-high-tint px-2 py-0.5 text-xs font-medium text-severity-high-ink"
								>
									Active issue
								</span>
							{/if}
						</div>
						<p class="mt-0.5 truncate text-xs text-ink-400">
							Owner: {asset.owner ?? 'Unassigned'} · Baseline set {ago(asset.last_checked_at)}
						</p>
					</div>
					<button
						onclick={() => remove(asset.urn)}
						disabled={busy.has(asset.urn)}
						class="shrink-0 rounded-full border border-line px-4 py-1.5 text-sm font-medium text-ink-600 transition-colors hover:bg-surface-sunken hover:text-ink-900 disabled:opacity-45"
					>
						{busy.has(asset.urn) ? 'Removing…' : 'Remove'}
					</button>
				</Card>
			{/each}
		</div>
	{/if}
</section>
