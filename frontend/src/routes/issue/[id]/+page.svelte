<script lang="ts">
	import { page } from '$app/state';
	import {
		getIssue,
		getAsset,
		getLineage,
		getExplanation,
		type Issue,
		type AssetMeta,
		type Lineage,
		type Explanation
	} from '$lib/api';
	import { humanize } from '$lib/format';
	import Card from '$lib/components/Card.svelte';
	import SeverityBadge from '$lib/components/SeverityBadge.svelte';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import ConfidenceLabel from '$lib/components/ConfidenceLabel.svelte';
	import BriefPanel from '$lib/components/BriefPanel.svelte';
	import WriteBackPanel from '$lib/components/WriteBackPanel.svelte';

	const issueId = page.params.id as string;

	let issue = $state<Issue | null>(null);
	let asset = $state<AssetMeta | null>(null);
	let lineage = $state<Lineage | null>(null);
	let loading = $state(true);
	let error = $state(false);

	let explanation = $state<Explanation | null>(null);
	let explaining = $state(true);

	$effect(() => {
		(async () => {
			try {
				const i = await getIssue(issueId);
				issue = i;
				[asset, lineage] = await Promise.all([getAsset(i.asset_id), getLineage(i.asset_id)]);
			} catch {
				error = true;
			} finally {
				loading = false;
			}

			// Generate the grounded explanation (non-blocking, degrades gracefully).
			try {
				explanation = await getExplanation(issueId);
			} catch {
				explanation = null;
			} finally {
				explaining = false;
			}
		})();
	});
</script>

<svelte:head>
	<title>{issue ? issue.asset_name : 'Issue'} · Dataco</title>
</svelte:head>

<a href="/" class="mb-6 inline-flex items-center gap-1 text-sm text-brand hover:underline">
	← Triage
</a>

{#if loading}
	<div class="h-64 animate-pulse rounded-2xl border border-line bg-surface-card"></div>
{:else if error || !issue}
	<div class="rounded-2xl border border-line bg-surface-card px-8 py-14 text-center">
		<h1 class="text-lg font-semibold">Issue not found</h1>
		<p class="mt-2 text-[15px] text-ink-600">
			It may have been resolved, or the API isn't reachable. Head back to the
			<a href="/" class="text-brand hover:underline">dashboard</a>.
		</p>
	</div>
{:else}
	<!-- Header -->
	<div class="mb-4 flex flex-wrap items-center gap-2">
		<SeverityBadge severity={issue.severity} />
		<StatusPill status={issue.status} />
		<span class="text-sm text-ink-400">{humanize(issue.issue_type)}</span>
	</div>
	<h1 class="mb-8 text-2xl font-semibold tracking-tight">{issue.asset_name}</h1>

	<div class="grid gap-5 lg:grid-cols-3">
		<!-- Left: metadata + schema + blast radius -->
		<div class="space-y-5 lg:col-span-1">
			<Card class="p-5">
				<h2 class="mb-4 text-sm font-semibold">Metadata</h2>
				<dl class="space-y-3.5 text-sm">
					<div>
						<dt class="text-xs text-ink-400">Owner</dt>
						<dd class="mt-0.5 {asset?.owner ? '' : 'text-ink-400'}">{asset?.owner ?? 'Unassigned'}</dd>
					</div>
					<div>
						<dt class="text-xs text-ink-400">Freshness</dt>
						<dd class="mt-0.5 text-ink-600">{asset?.freshness ?? '—'}</dd>
					</div>
					<div>
						<dt class="text-xs text-ink-400">Tags</dt>
						<dd class="mt-1.5 flex flex-wrap gap-1.5">
							{#each asset?.tags ?? [] as tag}
								<span class="rounded-md bg-surface-sunken px-2 py-0.5 text-xs text-ink-600">{tag}</span>
							{:else}
								<span class="text-ink-400">None</span>
							{/each}
						</dd>
					</div>
				</dl>
			</Card>

			{#if asset?.schema_fields?.length}
				<Card class="p-5">
					<h2 class="mb-3 text-sm font-semibold">Schema</h2>
					<ul class="divide-y divide-line font-mono text-xs">
						{#each asset.schema_fields as field}
							<li class="flex items-center justify-between py-2">
								<span class="text-ink-900">{field.name}</span>
								<span class="text-ink-400">{field.type}</span>
							</li>
						{/each}
					</ul>
				</Card>
			{/if}

			{#if lineage}
				<Card class="p-5">
					<h2 class="text-sm font-semibold">Blast radius</h2>
					<p class="mt-1 mb-3 text-xs text-ink-400">
						<span class="tabular-nums text-ink-600">{lineage.downstream.length}</span> downstream affected
					</p>
					<ul class="space-y-2 text-sm">
						{#each lineage.downstream as d}
							<li class="flex items-center gap-2 text-ink-600">
								<span class="h-1.5 w-1.5 shrink-0 rounded-full bg-severity-high"></span>
								<span class="truncate">{d.name}</span>
							</li>
						{:else}
							<li class="text-sm text-ink-400">No downstream assets found.</li>
						{/each}
					</ul>
				</Card>
			{/if}
		</div>

		<!-- Right: explanation -->
		<div class="space-y-5 lg:col-span-2">
			<Card class="p-6">
				<div class="mb-3 flex items-center justify-between">
					<h2 class="text-sm font-semibold">Explanation</h2>
					{#if explanation}<ConfidenceLabel confidence={explanation.confidence} />{/if}
				</div>

				{#if explaining}
					<div class="space-y-3">
						<div class="h-4 w-full animate-pulse rounded bg-surface-sunken"></div>
						<div class="h-4 w-11/12 animate-pulse rounded bg-surface-sunken"></div>
						<div class="h-4 w-4/6 animate-pulse rounded bg-surface-sunken"></div>
					</div>
				{:else if explanation}
					<p class="text-[15px] leading-relaxed text-ink-600">{explanation.summary}</p>
					{#if explanation.likely_cause}
						<div class="mt-5 border-t border-line pt-5">
							<h3 class="text-xs text-ink-400">Likely cause</h3>
							<p class="mt-1.5 text-[15px] leading-relaxed text-ink-600">{explanation.likely_cause}</p>
						</div>
					{/if}
					{#if explanation.recommended_action}
						<div class="mt-5 border-t border-line pt-5">
							<h3 class="text-xs text-ink-400">Recommended action</h3>
							<p class="mt-1.5 text-[15px] leading-relaxed text-ink-600">
								{explanation.recommended_action}
							</p>
						</div>
					{/if}
				{:else}
					<p class="text-[15px] leading-relaxed text-ink-400">
						Couldn't generate an explanation. Check that the API is reachable.
					</p>
				{/if}
			</Card>

			<BriefPanel issueId={issue.id} />

			<WriteBackPanel
				issueId={issue.id}
				tagUrn={issue.datahub_tag_urn}
				assertionUrn={issue.datahub_assertion_urn}
				writtenBackAt={issue.written_back_at}
			/>
		</div>
	</div>
{/if}
