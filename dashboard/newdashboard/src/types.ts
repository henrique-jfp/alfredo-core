export const ROOM_IDS = {
  LIVING: 'ROOM_LIVING',
  BEDROOM: 'ROOM_BEDROOM',
  LAURA: 'ROOM_LAURA',
  OFFICE: 'ROOM_OFFICE',
} as const;

export type RoomId = (typeof ROOM_IDS)[keyof typeof ROOM_IDS];

export const ROOM_LABELS: Record<RoomId, string> = {
  [ROOM_IDS.LIVING]: 'Sala de Estar',
  [ROOM_IDS.BEDROOM]: 'Quarto',
  [ROOM_IDS.LAURA]: 'Quarto da Laura',
  [ROOM_IDS.OFFICE]: 'Escritório',
};

export const DEFAULT_ROOM = ROOM_IDS.LIVING;

export interface Stats {
  interactions: number;
  active_timers: number;
  devices: number;
  tokens_used: number;
  ai_requests: number;
}

export interface HistoryItem {
  id: number;
  room_id: string;
  device_id: string;
  timestamp: string;
  input_text: string;
  output_text: string;
  latency_ms?: number;
}

export interface ListItem {
  id: number;
  content: string;
}

export interface TimerItem {
  id: number;
  timer_type: 'timer' | 'alarm';
  message: string;
  expires_at: string;
}

export interface Satellite {
  device_id: string;
  hardware: string;
  is_online: boolean;
  room_id: string;
  firmware_version: string;
  volume: number;
  brightness: number;
}

export interface Routine {
  id: number;
  name: string;
  trigger_value: string;
  room_id: string;
  action_value: string;
  is_active: boolean;
  days_of_week: string;
}

export interface Memory {
  id: number;
  fact: string;
  room_id: string;
  created_at: string;
}

export interface Weather {
  temperature: string;
  humidity: string;
  description: string;
  weather_code: number;
  max_temp: string;
  min_temp: string;
}
export interface AIMetrics {
  model: string;
  global_requests: number;
  total_tokens: number;
  rpm: number;
  tpm: number;
  avg_latency_ms: number;
  estimated_savings_usd: number;
  keys: {
    provider: string;
    requests: number;
    tokens: number;
  }[];
}

export interface CalendarEvent {
  id: number;
  title: string;
  start_time: string;
  time: string;
  date: string;
  day_name: string;
  room_id: string;
}

export interface IntegrationStatus {
  is_configured: boolean;
  is_connected: boolean;
}

export interface IntegrationsData {
  local_ip: string;
  spotify: IntegrationStatus;
  google_calendar: IntegrationStatus;
}

export interface ForecastHourly {
  dt: number;
  time: string;
  date: string;
  temp: number;
  feels_like: number;
  humidity: number;
  weather_code: number;
  description: string;
  icon: string;
  wind_speed: number;
  pop: number;
}

export interface ForecastDaily {
  date: string;
  max_temp: number;
  min_temp: number;
  weather_code: number;
  description: string;
  pop: number;
  moon_phase?: number;
  sunrise?: number;
  sunset?: number;
  moonrise?: number;
  moonset?: number;
  sunshine_duration?: number;
}

export interface ForecastCurrent {
  temperature: string;
  feels_like: string;
  humidity: string;
  pressure: string;
  description: string;
  weather_code: number;
  icon: string;
  max_temp: string;
  min_temp: string;
  wind_speed: string;
  wind_deg: number;
  visibility: number;
  sunrise: number;
  sunset: number;
  uvi?: number;
  dew_point?: number;
  wind_gust?: number;
  rain?: { "1h": number };
  is_day?: number;
}

export interface WeatherAlert {
  sender_name: string;
  event: string;
  start: number;
  end: number;
  description: string;
  tags?: string[];
}

export interface ForecastData {
  city: string;
  current: ForecastCurrent;
  hourly: ForecastHourly[];
  daily: ForecastDaily[];
  aqi?: number;
  alerts?: WeatherAlert[];
}

export interface TVConfig {
  configured: boolean;
  room_id: string;
  ip_address: string;
  mac_address: string;
  smartthings_pat: string;
  smartthings_device_id: string;
}

export interface SpotifyState {
  is_playing: boolean;
  track_name?: string;
  artist_name?: string;
  album_art?: string;
  progress_ms?: number;
  duration_ms?: number;
  device_name?: string;
  error?: string;
}

export type WeatherKind = 'sun' | 'cloud' | 'rain' | 'snow' | 'storm';

export function getWeatherKind(code: number): WeatherKind {
  // Códigos OpenWeatherMap (3 dígitos):
  // 2xx = Tempestade com trovão
  // 3xx = Garoa/chuvisco
  // 5xx = Chuva
  // 6xx = Neve
  // 7xx = Atmosfera (névoa, neblina)
  // 800 = Céu limpo
  // 80x = Nublado (801-804)
  if (code < 0)  return 'cloud';   // sem dado
  if (code >= 200 && code < 300) return 'storm';
  if (code >= 300 && code < 400) return 'rain';
  if (code >= 500 && code < 600) return 'rain';
  if (code >= 600 && code < 700) return 'snow';
  if (code >= 700 && code < 800) return 'cloud';  // névoa/neblina
  if (code === 800)               return 'sun';
  if (code >= 801 && code <= 804) return 'cloud';
  return 'cloud';
}

export const DREAM_THEME_GROUPS = {
  anxiety: ['ansiedade', 'medo', 'pesadelo', 'dragão', 'escuridão', 'queda', 'tsunami'],
  triumph: ['superação', 'vitória', 'voar', 'poder', 'força', 'luz'],
  introspection: ['introspecção', 'passado', 'infância', 'água', 'casa', 'família'],
  love: ['amor', 'paixão', 'encontro', 'abraço'],
} as const;

export interface Book {
  id: number;
  title: string;
  author: string | null;
  added_at: string;
  source_filename: string;
  format: 'pdf' | 'epub';
  total_chapters: number;
  cover_path: string | null;
  voice_name: string;
}

export interface BookChapter {
  id: number;
  book_id: number;
  index: number;
  title: string | null;
  has_annotation: boolean;
  has_audio: boolean;
}

export interface BookDetail extends Book {
  chapters: BookChapter[];
}
