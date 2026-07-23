<script lang="ts">
	import { getDashboard, runScan, type Issue } from '$lib/api';
	import { sortBySeverity } from '$lib/severity';
	import IssueCard from '$lib/components/IssueCard.svelte';

	let issues = $state<Issue[]>([]);
	let loading = $state(true);
	let error = $state(false);

	let scanning = $state(false);
	let scanMsg = $state('');
	let scanTimer: ReturnType<typeof setTimeout>;

	$effect(() => {
		getDashboard()
			.then((data) => (issues = sortBySeverity(data)))
			.catch(() => (error = true))
			.finally(() => (loading = false));
	});

	async function scan() {
		scanning = true;
		scanMsg = '';
		clearTimeout(scanTimer);
		try {
			const results = await runScan();
			const detected = results.filter((r) => r.detected).length;
			const noun = detected === 1 ? 'issue' : 'issues';
			scanMsg =
				detected > 0
					? `Scanned ${results.length} asset(s) · ${detected} new ${noun} detected & written back to DataHub.`
					: `Scanned ${results.length} asset(s) · no new issues.`;
			issues = sortBySeverity(await getDashboard());
			error = false;
		} catch {
			scanMsg = 'Scan failed — check that the API is running on localhost:8000.';
		} finally {
			scanning = false;
			scanTimer = setTimeout(() => (scanMsg = ''), 6000);
		}
	}
</script>

<svelte:head>
	<title>Dashboard · Dataco</title>
</svelte:head>

<header class="mb-8">
	<div class="flex items-start justify-between gap-4">
		<div>
			<h1 class="text-3xl font-semibold tracking-tight">Active trust issues</h1>
			{#if !loading && !error && issues.length > 0}
				<p class="mt-1.5 text-[15px] text-ink-600">
					{issues.length}
					{issues.length === 1 ? 'issue needs' : 'issues need'} attention, ranked by severity.
				</p>
			{/if}
		</div>
		<button
			onclick={scan}
			disabled={scanning}
			class="shrink-0 rounded-full bg-brand px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-ink disabled:opacity-60"
		>
			{scanning ? 'Scanning…' : 'Scan now'}
		</button>
	</div>
	{#if scanMsg}
		<p class="mt-3 text-[15px] text-ink-600">{scanMsg}</p>
	{/if}
</header>

{#if loading}
	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each Array(6) as _, i (i)}
			<div class="h-36 animate-pulse rounded-2xl border border-line bg-surface-card"></div>
		{/each}
	</div>
{:else if error}
	<div class="rounded-2xl border border-line bg-surface-card px-8 py-14 text-center">
		<h2 class="text-lg font-semibold">Can't reach the monitoring service</h2>
		<p class="mx-auto mt-2 max-w-md text-[15px] text-ink-600">
			Make sure the API is running on <span class="text-ink-900">localhost:8000</span>, then refresh.
		</p>
	</div>
{:else if issues.length === 0}
	<div class="rounded-2xl border border-line bg-surface-card px-8 py-14 text-center">
		<h2 class="text-lg font-semibold">All clear</h2>
		<p class="mx-auto mt-2 max-w-md text-[15px] text-ink-600">
			Every watched dataset is passing its freshness, schema, and ownership checks. New issues appear
			here the moment monitoring detects drift.
		</p>
	</div>
{:else}
	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each issues as issue (issue.id)}
			<IssueCard {issue} />
		{/each}
	</div>
{/if}
