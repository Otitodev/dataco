/** Compact relative time, e.g. "just now", "12m ago", "3h ago", "2d ago". */
export function timeAgo(iso: string): string {
	const then = new Date(iso).getTime();
	if (Number.isNaN(then)) return '';
	const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
	if (secs < 60) return 'just now';
	const mins = Math.floor(secs / 60);
	if (mins < 60) return `${mins}m ago`;
	const hrs = Math.floor(mins / 60);
	if (hrs < 24) return `${hrs}h ago`;
	return `${Math.floor(hrs / 24)}d ago`;
}

/** "schema_drift" → "Schema drift" */
export function humanize(value: string): string {
	const s = value.replaceAll('_', ' ').trim();
	return s.charAt(0).toUpperCase() + s.slice(1);
}
