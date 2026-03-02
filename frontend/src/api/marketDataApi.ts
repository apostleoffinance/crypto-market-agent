import type { TopCoinsResponse, SummaryResponse, QuarterDatesResponse } from '../types';

// In dev, Vite proxy handles /api → localhost:8000
// In production (Vercel), VITE_API_URL points to your Railway backend
const BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

interface TopCoinsParams {
  topN?: number;
  startYear?: number;
  endYear?: number;
  position?: string;
  quarters?: string;
  columns?: string[];
}

function buildTopCoinsSearch(params: TopCoinsParams): URLSearchParams {
  const sp = new URLSearchParams();
  if (params.topN) sp.set('top_n', String(params.topN));
  if (params.startYear) sp.set('start_year', String(params.startYear));
  if (params.endYear) sp.set('end_year', String(params.endYear));
  if (params.position) sp.set('position', params.position);
  if (params.quarters) sp.set('quarters', params.quarters);
  if (params.columns && params.columns.length > 0) sp.set('columns', params.columns.join(','));
  return sp;
}

export async function fetchTopCoins(params: TopCoinsParams): Promise<TopCoinsResponse> {
  const sp = buildTopCoinsSearch(params);
  const res = await fetch(`${BASE}/top-coins?${sp}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchSummary(): Promise<SummaryResponse> {
  const res = await fetch(`${BASE}/summary`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchQuarters(params: {
  startYear?: number;
  endYear?: number;
  position?: string;
} = {}): Promise<QuarterDatesResponse> {
  const sp = new URLSearchParams();
  if (params.startYear) sp.set('start_year', String(params.startYear));
  if (params.endYear) sp.set('end_year', String(params.endYear));
  if (params.position) sp.set('position', params.position);

  const res = await fetch(`${BASE}/quarters?${sp}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchCoinAtDate(coinId: string, date: string): Promise<any> {
  const res = await fetch(`${BASE}/coin/${coinId}?date=${date}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function getExportUrl(params: TopCoinsParams): string {
  const sp = buildTopCoinsSearch(params);
  return `${BASE}/top-coins/export?${sp}`;
}

export async function downloadExportCSV(params: TopCoinsParams): Promise<void> {
  const url = getExportUrl(params);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = res.headers.get('content-disposition')?.split('filename=')[1] || 'crypto_data.csv';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}
