const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export interface Issue {
	id: string;
	asset_id: string;
	asset_name: string;
	issue_type: string;
	severity: 'low' | 'medium' | 'high' | 'critical';
	status: 'active' | 'investigating' | 'resolved';
	summary: string;
	likely_cause: string;
	impacted_assets: string[];
	blast_radius: number;
	owner: string | null;
	confidence: 'high' | 'medium' | 'low';
	created_at: string;
	updated_at: string;
	resolved_at: string | null;
	datahub_tag_urn?: string | null;
	datahub_assertion_urn?: string | null;
	written_back_at?: string | null;
}

export interface ScanResult {
	urn: string;
	detected: boolean;
	issue_id: string | null;
	issue_type: string | null;
	severity: string | null;
	tag_urn: string | null;
	assertion_urn: string | null;
	detail: string;
}

export interface WriteBackResult {
	issue_id: string;
	ok: boolean;
	tag_urn: string | null;
	assertion_urn: string | null;
	detail: string;
}

export interface ScanStatus {
	enabled: boolean;
	interval_seconds: number;
	last_run_at: string | null;
	last_scanned: number;
	last_detected: number;
	watch_count: number;
}

export interface Brief {
	id: string;
	issue_id: string;
	subject: string;
	what_happened: string;
	what_is_affected: string[];
	who_to_contact: string;
	next_step: string;
	estimated_impact: 'low' | 'medium' | 'high' | 'critical';
	generated_at: string;
}

export interface AssetMeta {
	id: string;
	name: string;
	description: string;
	owner: string | null;
	schema_fields: { name: string; type: string }[];
	freshness: string | null;
	tags: string[];
	docs: string | null;
}

export interface Lineage {
	upstream: { id: string; name: string }[];
	downstream: { id: string; name: string }[];
}

export interface Explanation {
	summary: string;
	likely_cause: string;
	impacted_assets: string[];
	confidence: 'high' | 'medium' | 'low';
	recommended_action: string;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${API_BASE}${url}`, {
		headers: { 'Content-Type': 'application/json' },
		...init
	});
	if (!res.ok) {
		throw new Error(`${res.status} ${res.statusText}`);
	}
	return res.json();
}

export async function getDashboard(): Promise<Issue[]> {
	return fetchJson<Issue[]>('/dashboard');
}

export async function getIssue(id: string): Promise<Issue> {
	return fetchJson<Issue>(`/issue/${id}`);
}

export async function getAsset(id: string): Promise<AssetMeta> {
	return fetchJson<AssetMeta>(`/asset/${id}`);
}

export async function getLineage(id: string): Promise<Lineage> {
	return fetchJson<Lineage>(`/lineage/${id}`);
}

export async function searchAssets(query: string): Promise<AssetMeta[]> {
	return fetchJson<AssetMeta[]>(`/search?q=${encodeURIComponent(query)}`);
}

export async function getExplanation(issueId: string): Promise<Explanation> {
	return fetchJson<Explanation>('/explain', {
		method: 'POST',
		body: JSON.stringify({ issue_id: issueId })
	});
}

export async function generateBrief(issueId: string): Promise<Brief> {
	return fetchJson<Brief>('/brief', {
		method: 'POST',
		body: JSON.stringify({ issue_id: issueId })
	});
}

export async function updateIssueStatus(id: string, status: string): Promise<Issue> {
	return fetchJson<Issue>(`/issue/${id}`, {
		method: 'PATCH',
		body: JSON.stringify({ status })
	});
}

export async function addIssueNote(issueId: string, noteText: string, author: string): Promise<void> {
	await fetchJson(`/issue/${issueId}/note`, {
		method: 'POST',
		body: JSON.stringify({ note_text: noteText, author })
	});
}

export async function runScan(urns?: string[]): Promise<ScanResult[]> {
	return fetchJson<ScanResult[]>('/scan', {
		method: 'POST',
		body: JSON.stringify({ urns: urns ?? null })
	});
}

export async function writeBackIssue(issueId: string): Promise<WriteBackResult> {
	return fetchJson<WriteBackResult>(`/issue/${issueId}/writeback`, {
		method: 'POST'
	});
}

export async function getScanStatus(): Promise<ScanStatus> {
	return fetchJson<ScanStatus>('/scan/status');
}
