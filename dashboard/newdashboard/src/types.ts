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
