<script lang="ts">
	import { SEVERITY, type Severity } from '$lib/severity';

	let { severity }: { severity: Severity } = $props();
	const s = $derived(SEVERITY[severity]);
</script>

<span
	class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium {s.badge}"
>
	<span class="h-1.5 w-1.5 rounded-full {s.dot}"></span>
	{s.label}
</span>
