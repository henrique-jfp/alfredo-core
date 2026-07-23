import {
  Stats,
  HistoryItem,
  ListItem,
  TimerItem,
  Satellite,
  Routine,
  Memory,
  Weather,
  AIMetrics,
  CalendarEvent,
  IntegrationsData,
  ForecastData,
  TVConfig,
} from '../types';

/**
 * Default timeout for all API requests (15 seconds).
 * If a backend endpoint hangs, the request will abort and throw
 * instead of blocking the UI indefinitely.
 */
const API_TIMEOUT_MS = 15_000;

async function fetchFromAPI<T>(url: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const errBody = await response.json();
        if (errBody.detail) detail = errBody.detail;
        else if (errBody.error) detail = errBody.error;
      } catch {}
      throw new Error(detail);
    }
    return await response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  getStats: () => fetchFromAPI<Stats>('/api/dashboard/stats'),
  getAIMetrics: () => fetchFromAPI<AIMetrics>('/api/dashboard/ai_metrics'),
  getHistory: () => fetchFromAPI<HistoryItem[]>('/api/dashboard/history'),
  getLists: () => fetchFromAPI<{ compras: ListItem[]; tarefas: ListItem[] }>('/api/dashboard/lists'),
  getTimers: () => fetchFromAPI<TimerItem[]>('/api/dashboard/timers'),
  deleteTimer: (id: number) => fetchFromAPI<{ success: boolean }>(`/api/dashboard/timers/${id}`, { method: 'DELETE' }),
  getSatellites: () => fetchFromAPI<Satellite[]>('/api/satellite/devices'),
  getRoutines: () => fetchFromAPI<Routine[]>('/api/dashboard/routines'),
  getMemories: () => fetchFromAPI<Memory[]>('/api/dashboard/memories'),
  createMemory: (data: { fact: string }) => fetchFromAPI<Memory>('/api/dashboard/memories', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }),
  deleteMemory: (id: number) => fetchFromAPI<{ success: boolean }>(`/api/dashboard/memories/${id}`, { method: 'DELETE' }),
  updateMemory: (id: number, fact: string) => fetchFromAPI<{ success: boolean }>(`/api/dashboard/memories/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fact })
  }),
  getWeather: () => fetchFromAPI<Weather>('/api/weather/current'),
  createRoutine: (data: Record<string, unknown>) => fetchFromAPI<Routine>('/api/dashboard/routines', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }),
  deleteRoutine: (id: number) => fetchFromAPI<{ success: boolean }>(`/api/dashboard/routines/${id}`, { method: 'DELETE' }),
  getDreams: () => fetchFromAPI<{ history: any[]; word_freq: Record<string, number> }>('/api/dashboard/dreams'),
  createDream: (text: string) => fetchFromAPI<{ success: boolean; dream: unknown }>('/api/dashboard/dreams', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  }),
  getSettings: () => fetchFromAPI<Record<string, string>>('/api/dashboard/settings'),
  saveSettings: (settings: Record<string, string>) => fetchFromAPI<{ success: boolean }>('/api/dashboard/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ settings })
  }),
  getEvents: (start?: string, end?: string) => {
    const params = new URLSearchParams();
    if (start) params.set('start', start);
    if (end) params.set('end', end);
    const qs = params.toString();
    return fetchFromAPI<{ events: CalendarEvent[] }>(`/api/dashboard/events${qs ? `?${qs}` : ''}`);
  },
  createEvent: (data: { title: string; start_time: string; room_id?: string }) => fetchFromAPI<CalendarEvent>('/api/dashboard/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }),
  deleteEvent: (id: number) => fetchFromAPI<{ success: boolean }>(`/api/dashboard/events/${id}`, { method: 'DELETE' }),
  getForecast: () => fetchFromAPI<ForecastData>('/api/weather/forecast'),
  getIntegrations: () => fetchFromAPI<IntegrationsData>('/api/dashboard/integrations'),
  getLocations: () => fetchFromAPI<Record<string, unknown>[]>('/api/dashboard/locations'),
  createLocation: (data: Record<string, unknown>) => fetchFromAPI<Record<string, unknown>>('/api/dashboard/locations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }),
  deleteLocation: (id: number) => fetchFromAPI<{ success: boolean }>(`/api/dashboard/locations/${id}`, { method: 'DELETE' }),

  // Commands
  sendCommand: (command: string) => fetchFromAPI<{ success: boolean }>('/api/dashboard/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command })
  }),

  // TV Integration
  getTVConfig: (roomId: string) => fetchFromAPI<TVConfig>(`/api/tv/config/${roomId}`),
  saveTVConfig: (data: {
    room_id: string;
    ip_address: string;
    mac_address: string;
    smartthings_pat: string;
    smartthings_device_id: string;
  }) => fetchFromAPI<{ success: boolean }>('/api/tv/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }),
  controlTV: (roomId: string, action: string, state?: string) =>
    fetchFromAPI<{ success: boolean }>(`/api/tv/control/${roomId}/${action}${state !== undefined ? `?state=${state}` : ''}`, { method: 'POST' }),

  // Spotify
  controlSpotify: (action: string) => fetchFromAPI<{ success: boolean }>('/api/spotify/control', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action })
  }),

  // Integrations
  saveSpotifyCredentials: (client_id: string, client_secret: string) =>
    fetchFromAPI<{ success: boolean; detail?: string }>('/api/dashboard/integrations/spotify/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id, client_secret })
    }),
  testSpotify: () => fetchFromAPI<{ status: string; error?: string }>('/api/dashboard/integrations/spotify/test', { method: 'POST' }),
  connectSpotify: () => { window.location.href = '/api/spotify/login'; },
  connectGoogleCalendar: () => { window.location.href = '/api/auth/google/authorize'; },
  syncGoogleCalendar: () => fetchFromAPI<{ success: boolean }>('/api/auth/google/sync', { method: 'POST' }),
};
