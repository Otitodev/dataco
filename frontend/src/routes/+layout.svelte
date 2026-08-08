<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';

	const { children } = $props();

	const nav = [
		{ href: '/', label: 'Dashboard' },
		{ href: '/monitoring', label: 'Monitoring' },
		{ href: '/search', label: 'Search' }
	];
</script>

<svelte:head>
	<title>Dataco</title>
</svelte:head>

<div class="min-h-screen bg-surface-page text-ink-900">
	<header class="sticky top-0 z-10 border-b border-line bg-surface-card/80 backdrop-blur-xl">
		<div class="mx-auto flex max-w-5xl items-center justify-between px-6 py-3.5">
			<a href="/" class="text-[17px] font-semibold tracking-tight">Dataco</a>
			<nav class="flex gap-1 text-sm">
				{#each nav as item}
					{@const active = page.url.pathname === item.href}
					<a
						href={item.href}
						class="rounded-full px-3.5 py-1.5 transition-colors {active
							? 'bg-surface-sunken font-medium text-ink-900'
							: 'text-ink-600 hover:text-ink-900'}"
					>
						{item.label}
					</a>
				{/each}
			</nav>
		</div>
	</header>

	<main class="mx-auto max-w-5xl px-6 py-10">
		{@render children?.()}
	</main>
</div>
