import { SessionResponse, SystemHealthResponse } from '../types';

const API_BASE = '/api/v1';

export async function createAnalysis(query: string, providerPreference: string = 'auto'): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, provider_preference: providerPreference })
  });
  if (!res.ok) {
    throw new Error(`Failed to create analysis: ${res.statusText}`);
  }
  return res.json();
}

export async function getAnalysisSession(sessionId: string): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/analysis/${sessionId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch session ${sessionId}: ${res.statusText}`);
  }
  return res.json();
}

export async function listAnalysisSessions(): Promise<SessionResponse[]> {
  const res = await fetch(`${API_BASE}/analysis`);
  if (!res.ok) {
    throw new Error(`Failed to fetch history: ${res.statusText}`);
  }
  return res.json();
}

export async function getSystemHealth(): Promise<SystemHealthResponse> {
  const res = await fetch(`${API_BASE}/llm/health`);
  if (!res.ok) {
    throw new Error(`Failed to fetch system health: ${res.statusText}`);
  }
  return res.json();
}

export async function listDatasets(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/datasets`);
  if (!res.ok) {
    throw new Error(`Failed to fetch datasets: ${res.statusText}`);
  }
  return res.json();
}
