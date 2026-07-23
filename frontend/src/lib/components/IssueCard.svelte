<script lang="ts">
	import type { Issue } from '$lib/api';
	import { timeAgo, humanize } from '$lib/format';
	import Card from './Card.svelte';
	import SeverityBadge from './SeverityBadge.svelte';

	let { issue }: { issue: Issue } = $props();
</script>

<Card href={`/issue/${issue.id}`} class="p-5">
	<div class="mb-3 flex items-center justify-between">
		<SeverityBadge severity={issue.severity} />
		<span class="text-xs text-ink-400">{timeAgo(issue.created_at)}</span>
	</div>

	<h3 class="truncate text-[15px] font-semibold tracking-tight text-ink-900">{issue.asset_name}</h3>
	<p class="mt-0.5 text-sm text-ink-600">{humanize(issue.issue_type)}</p>

	<div class="mt-4 flex items-center justify-between border-t border-line pt-3 text-xs text-ink-400">
		<span class="truncate">{issue.owner ?? 'Unassigned'}</span>
		<span class="tabular-nums whitespace-nowrap">
			<span class="font-medium text-ink-600">{issue.blast_radius}</span> downstream
		</span>
	</div>
</Card>
