import {
  Stats,
  HistoryItem,
  ListItem,
  TimerItem,
  Satellite,
  Routine,
  Memory,
  Weather,
  AIMetrics
} from '../types';

// Helper to fetch directly from the backend
async function fetchFromAPI<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error('Network response was not ok: ' + response.statusText);
  return await response.json();
}

export const api = {
  getStats: () => fetchFromAPI<Stats>('/api/dashboard/stats'),
  getAIMetrics: () => fetchFromAPI<AIMetrics>('/api/dashboard/ai_metrics'),
  getHistory: () => fetchFromAPI<HistoryItem[]>('/api/dashboard/history'),
  getLists: () => fetchFromAPI<{ compras: ListItem[]; tarefas: ListItem[] }>('/api/dashboard/lists'),
  getTimers: () => fetchFromAPI<TimerItem[]>('/api/dashboard/timers'),
  getSatellites: () => fetchFromAPI<Satellite[]>('/api/satellite/devices'),
  getRoutines: () => fetchFromAPI<Routine[]>('/api/dashboard/routines'),
  getMemories: () => fetchFromAPI<Memory[]>('/api/dashboard/memories'),
  createMemory: (data: { fact: string }) => fetchFromAPI<Memory>('/api/dashboard/memories', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }),
  deleteMemory: (id: number) => fetchFromAPI<any>(`/api/dashboard/memories/${id}`, { method: 'DELETE' }),
  updateMemory: (id: number, fact: string) => fetchFromAPI<any>(`/api/dashboard/memories/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fact })
  }),
  getWeather: () => fetchFromAPI<Weather>('/api/weather/current'),
  createRoutine: (data: any) => fetchFromAPI<Routine>('/api/dashboard/routines', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }),
  deleteRoutine: (id: number) => fetchFromAPI<any>(`/api/dashboard/routines/${id}`, { method: 'DELETE' }),
  getDreams: () => fetchFromAPI<{history: any[], word_freq: Record<string, number>}>('/api/dashboard/dreams'),
  createDream: (text: string) => fetchFromAPI<any>('/api/dashboard/dreams', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  }),
  getSettings: () => fetchFromAPI<Record<string, string>>('/api/dashboard/settings'),
  saveSettings: (settings: Record<string, string>) => fetchFromAPI<any>('/api/dashboard/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ settings })
  })
};
