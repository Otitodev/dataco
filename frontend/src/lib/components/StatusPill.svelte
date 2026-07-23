<script lang="ts">
	import { STATUS, type Status } from '$lib/severity';

	let { status }: { status: Status } = $props();
	const s = $derived(STATUS[status]);
</script>

<span
	class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium {s.badge}"
>
	<span class="h-1.5 w-1.5 rounded-full {s.dot}"></span>
	{s.label}
</span>
