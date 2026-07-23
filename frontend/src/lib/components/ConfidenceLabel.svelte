<script lang="ts">
	import { CONFIDENCE, type Confidence } from '$lib/severity';

	// confidence may be null/absent (e.g. before an explanation is generated).
	let { confidence }: { confidence: Confidence | null | undefined } = $props();
	const c = $derived(confidence ? CONFIDENCE[confidence] : undefined);
</script>

{#if c}
	<span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {c.badge}">
		{c.label}
	</span>
{/if}
