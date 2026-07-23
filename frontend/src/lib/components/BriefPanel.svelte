<script lang="ts">
	import { generateBrief, type Brief } from '$lib/api';
	import SeverityBadge from './SeverityBadge.svelte';

	let { issueId }: { issueId: string } = $props();

	let brief = $state<Brief | null>(null);
	let generating = $state(false);
	let error = $state(false);
	let copied = $state(false);

	async function generate() {
		generating = true;
		error = false;
		try {
			brief = await generateBrief(issueId);
		} catch {
			error = true;
		} finally {
			generating = false;
		}
	}

	function toMarkdown(b: Brief): string {
		return [
			`# ${b.subject}`,
			``,
			`**What happened**`,
			b.what_happened,
			``,
			`**What's affected**`,
			...b.what_is_affected.map((a) => `- ${a}`),
			``,
			`**Who to contact**`,
			b.who_to_contact,
			``,
			`**Next step**`,
			b.next_step,
			``,
			`**Estimated impact:** ${b.estimated_impact}`,
			``
		].join('\n');
	}

	async function copy() {
		if (!brief) return;
		await navigator.clipboard.writeText(toMarkdown(brief));
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}

	function exportMarkdown() {
		if (!brief) return;
		const blob = new Blob([toMarkdown(brief)], { type: 'text/markdown' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `brief-${issueId}.md`;
		a.click();
		URL.revokeObjectURL(url);
	}
</script>

<div class="rounded-2xl border border-line bg-surface-card p-6">
	<div class="flex items-center justify-between">
		<h2 class="text-sm font-semibold">Stakeholder brief</h2>
		{#if brief}
			<div class="flex items-center gap-1">
				<button
					onclick={copy}
					class="rounded-full px-3 py-1 text-xs font-medium text-brand transition-colors hover:bg-surface-sunken"
				>
					{copied ? 'Copied' : 'Copy'}
				</button>
				<button
					onclick={exportMarkdown}
					class="rounded-full px-3 py-1 text-xs font-medium text-brand transition-colors hover:bg-surface-sunken"
				>
					Export
				</button>
			</div>
		{/if}
	</div>

	{#if !brief && !generating}
		<p class="mt-2 max-w-md text-[15px] leading-relaxed text-ink-600">
			Turn this issue into a plain-language summary for non-technical stakeholders, grounded only in
			the metadata above.
		</p>
		<button
			onclick={generate}
			class="mt-4 rounded-full bg-brand px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-ink"
		>
			Generate brief
		</button>
		{#if error}
			<p class="mt-3 text-sm text-severity-critical-ink">
				Couldn't generate the brief. Check the API and try again.
			</p>
		{/if}
	{:else if generating}
		<div class="mt-4 space-y-3">
			<div class="h-5 w-2/3 animate-pulse rounded bg-surface-sunken"></div>
			<div class="h-4 w-full animate-pulse rounded bg-surface-sunken"></div>
			<div class="h-4 w-5/6 animate-pulse rounded bg-surface-sunken"></div>
		</div>
	{:else if brief}
		<div class="mt-4 space-y-5">
			<p class="text-lg font-semibold tracking-tight text-ink-900">{brief.subject}</p>

			<div>
				<h3 class="text-xs text-ink-400">What happened</h3>
				<p class="mt-1 text-[15px] leading-relaxed text-ink-600">{brief.what_happened}</p>
			</div>

			<div>
				<h3 class="text-xs text-ink-400">What's affected</h3>
				<ul class="mt-1.5 space-y-1 text-[15px] text-ink-600">
					{#each brief.what_is_affected as item}
						<li class="flex items-center gap-2">
							<span class="h-1.5 w-1.5 shrink-0 rounded-full bg-severity-high"></span>
							<span>{item}</span>
						</li>
					{/each}
				</ul>
			</div>

			<div class="grid gap-5 sm:grid-cols-2">
				<div>
					<h3 class="text-xs text-ink-400">Who to contact</h3>
					<p class="mt-1 text-[15px] text-ink-600">{brief.who_to_contact}</p>
				</div>
				<div>
					<h3 class="text-xs text-ink-400">Next step</h3>
					<p class="mt-1 text-[15px] text-ink-600">{brief.next_step}</p>
				</div>
			</div>

			<div class="flex items-center gap-2 border-t border-line pt-4">
				<span class="text-xs text-ink-400">Estimated impact</span>
				<SeverityBadge severity={brief.estimated_impact} />
			</div>
		</div>
	{/if}
</div>
