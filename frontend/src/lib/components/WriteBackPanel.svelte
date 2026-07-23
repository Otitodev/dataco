<script lang="ts">
	import { untrack } from 'svelte';
	import { writeBackIssue, type WriteBackResult } from '$lib/api';

	let {
		issueId,
		tagUrn = null,
		assertionUrn = null,
		writtenBackAt = null
	}: {
		issueId: string;
		tagUrn?: string | null;
		assertionUrn?: string | null;
		writtenBackAt?: string | null;
	} = $props();

	// Seed the "done" state once from persisted provenance so a reload of an
	// already-written issue renders the result rather than the idle prompt.
	// untrack() makes the one-time snapshot explicit (props don't change here).
	let result = $state<WriteBackResult | null>(
		untrack(() =>
			writtenBackAt
				? { issue_id: issueId, ok: true, tag_urn: tagUrn, assertion_urn: assertionUrn, detail: '' }
				: null
		)
	);
	let writing = $state(false);
	let error = $state(false);

	async function write() {
		writing = true;
		error = false;
		try {
			result = await writeBackIssue(issueId);
		} catch {
			error = true;
		} finally {
			writing = false;
		}
	}
</script>

<div class="rounded-2xl border border-line bg-surface-card p-6">
	<h2 class="text-sm font-semibold">Write back to DataHub</h2>

	{#if !result && !writing}
		<p class="mt-2 max-w-md text-[15px] leading-relaxed text-ink-600">
			Record this issue on the asset in DataHub — a <span class="font-mono text-[13px]">trust:</span>
			tag and a failing custom assertion, so the signal lives in the catalog.
		</p>
		<button
			onclick={write}
			class="mt-4 rounded-full bg-brand px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-ink"
		>
			Write back
		</button>
		{#if error}
			<p class="mt-3 text-sm text-severity-critical-ink">
				Couldn't write back. Check the API and try again.
			</p>
		{/if}
	{:else if writing}
		<div class="mt-4 space-y-3">
			<div class="h-4 w-2/3 animate-pulse rounded bg-surface-sunken"></div>
			<div class="h-4 w-1/2 animate-pulse rounded bg-surface-sunken"></div>
		</div>
	{:else if result}
		{#if result.ok}
			<div class="mt-3 flex items-center gap-2 text-[15px] text-ink-900">
				<span
					class="flex h-5 w-5 items-center justify-center rounded-full border border-line text-xs"
					aria-hidden="true">✓</span
				>
				<span>Written back to DataHub</span>
			</div>
			<dl class="mt-4 space-y-3">
				<div>
					<dt class="text-xs text-ink-400">Tag</dt>
					<dd class="mt-0.5 break-all font-mono text-xs text-ink-600">
						{result.tag_urn ?? '—'}
					</dd>
				</div>
				<div>
					<dt class="text-xs text-ink-400">Assertion (FAILURE)</dt>
					<dd class="mt-0.5 break-all font-mono text-xs text-ink-600">
						{result.assertion_urn ?? '—'}
					</dd>
				</div>
			</dl>
			<button
				onclick={write}
				class="mt-4 rounded-full px-3 py-1 text-xs font-medium text-brand transition-colors hover:bg-surface-sunken"
			>
				Write back again
			</button>
		{:else}
			<p class="mt-3 text-[15px] text-ink-600">
				Nothing was written back{result.detail ? ` — ${result.detail}` : ''}.
			</p>
			<button
				onclick={write}
				class="mt-4 rounded-full bg-brand px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-ink"
			>
				Try again
			</button>
		{/if}
	{/if}
</div>
