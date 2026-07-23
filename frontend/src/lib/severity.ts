// Single source of truth for how severity, status, and confidence look.
// Class strings are written as complete literals so Tailwind's scanner
// generates them — never build these by interpolation.

export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type Status = 'active' | 'investigating' | 'resolved';
export type Confidence = 'high' | 'medium' | 'low';

export const SEVERITY_ORDER: Record<Severity, number> = {
	critical: 0,
	high: 1,
	medium: 2,
	low: 3
};

interface SeverityStyle {
	label: string;
	bar: string; // vivid left spine
	badge: string; // tint background + AA-contrast ink
	dot: string; // vivid status dot
}

export const SEVERITY: Record<Severity, SeverityStyle> = {
	critical: {
		label: 'Critical',
		bar: 'bg-severity-critical',
		badge: 'bg-severity-critical-tint text-severity-critical-ink',
		dot: 'bg-severity-critical'
	},
	high: {
		label: 'High',
		bar: 'bg-severity-high',
		badge: 'bg-severity-high-tint text-severity-high-ink',
		dot: 'bg-severity-high'
	},
	medium: {
		label: 'Medium',
		bar: 'bg-severity-medium',
		badge: 'bg-severity-medium-tint text-severity-medium-ink',
		dot: 'bg-severity-medium'
	},
	low: {
		label: 'Low',
		bar: 'bg-severity-low',
		badge: 'bg-severity-low-tint text-severity-low-ink',
		dot: 'bg-severity-low'
	}
};

export const STATUS: Record<Status, { label: string; badge: string; dot: string }> = {
	active: {
		label: 'Active',
		badge: 'bg-severity-critical-tint text-severity-critical-ink',
		dot: 'bg-severity-critical'
	},
	investigating: {
		label: 'Investigating',
		badge: 'bg-severity-medium-tint text-severity-medium-ink',
		dot: 'bg-severity-medium'
	},
	resolved: {
		label: 'Resolved',
		badge: 'bg-surface-sunken text-ink-600',
		dot: 'bg-severity-resolved'
	}
};

export const CONFIDENCE: Record<Confidence, { label: string; badge: string }> = {
	high: { label: 'High confidence', badge: 'bg-severity-low-tint text-severity-low-ink' },
	medium: { label: 'Medium confidence', badge: 'bg-severity-medium-tint text-severity-medium-ink' },
	low: { label: 'Low confidence', badge: 'bg-surface-sunken text-ink-600' }
};

export function sortBySeverity<T extends { severity: Severity }>(items: T[]): T[] {
	return [...items].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
}
