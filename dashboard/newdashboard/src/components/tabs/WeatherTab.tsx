import React, { useMemo } from 'react';
import { getWeatherKind } from '../../types';
import type { WeatherAlert } from '../../types';
import { SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import { WeatherIconByCode } from '../WeatherDisplay';
import {
  Droplets, Wind, Eye, Gauge, Sun, Moon,
  ArrowUp, ArrowDown, MapPin, AlertTriangle,
  Thermometer, Sunrise, Sunset, CloudRain,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useWeather } from '../../hooks/useWeather';

// ─── Helpers ───────────────────────────────────────────────────────────────

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function dayLabel(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  if (dateStr === today.toISOString().slice(0, 10)) return 'Hoje';
  if (dateStr === tomorrow.toISOString().slice(0, 10)) return 'Amanhã';
  return d.toLocaleDateString('pt-BR', { weekday: 'short' }).replace('-feira', '');
}

function windDir(deg: number) {
  const dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  return dirs[Math.round(deg / 22.5) % 16];
}

// ─── Sub-components ────────────────────────────────────────────────────────

function AlertBanner({ alerts }: { alerts: WeatherAlert[] }) {
  if (!alerts?.length) return null;
  const a = alerts[0];
  return (
    <div className="rounded-xl border border-rose-500/25 bg-rose-500/8 p-3 md:p-4 flex items-start gap-3 backdrop-blur-sm">
      <AlertTriangle className="h-5 w-5 shrink-0 text-rose-400 mt-0.5" />
      <div className="min-w-0">
        <p className="text-[13px] font-bold uppercase tracking-wider text-rose-300">{a.event}</p>
        <p className="text-[12px] text-rose-400/80 line-clamp-2 mt-0.5">{a.description}</p>
      </div>
    </div>
  );
}

function MiniDetail({ icon: Icon, label, value }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2.5">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/5">
        <Icon className="h-4 w-4 text-white/70" />
      </div>
      <div className="min-w-0">
        <div className="text-[9px] font-bold uppercase tracking-[0.15em] text-white/50">{label}</div>
        <div className="text-[14px] font-semibold text-white tabular-nums mt-0.5">{value}</div>
      </div>
    </div>
  );
}

function SunArc({ sunrise, sunset, current }: { sunrise: number; sunset: number; current: number }) {
  const total = sunset - sunrise;
  const elapsed = current - sunrise;
  const pct = total > 0 ? Math.max(0, Math.min(1, elapsed / total)) : 0;
  const cx = 6 + pct * 88;
  const cy = 36 - Math.sin(pct * Math.PI) * 28;

  return (
    <div className="relative w-full h-14 pt-1">
      <svg viewBox="0 0 100 40" className="w-full h-full overflow-visible">
        {/* Arc path */}
        <path d="M 6 36 Q 50 2 94 36" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="1.5" strokeDasharray="3 3" />
        {/* Sun position */}
        {pct > 0 && pct < 1 && (
          <g>
            <circle cx={cx} cy={cy} r="5" fill="#fbbf24" filter="url(#sun-glow-arc)">
              <animate attributeName="r" values="4;6;4" dur="2s" repeatCount="indefinite" />
            </circle>
            <circle cx={cx} cy={cy} r="10" fill="rgba(251,191,36,0.15)">
              <animate attributeName="r" values="8;12;8" dur="2s" repeatCount="indefinite" />
            </circle>
          </g>
        )}
      </svg>
      <div className="flex justify-between text-[10px] text-white/50 font-mono -mt-1">
        <span>{formatTime(sunrise)}</span>
        <span>{formatTime(sunset)}</span>
      </div>
      <defs>
        <radialGradient id="sun-glow-arc">
          <stop offset="0%" stopColor="#fbbf24" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#fbbf24" stopOpacity="0" />
        </radialGradient>
      </defs>
    </div>
  );
}

// ─── Main Tab ──────────────────────────────────────────────────────────────

export function WeatherTab() {
  const { data, loading, error } = useWeather();
  const [unit, setUnit] = React.useState<'C' | 'F'>('C');

  const parseT = (v: string | number) => {
    const n = typeof v === 'string' ? parseInt(v) : v;
    return unit === 'C' ? n : Math.round(n * 9 / 5 + 32);
  };
  const fmtT = (v: string | number) => `${parseT(v)}°`;

  // Loading state
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-2 border-brass-400/30 border-t-brass-300 animate-spin" />
          <p className="text-sm text-[color:var(--text-tertiary)]">Carregando dados atmosféricos...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center max-w-md">
          <CloudRain className="h-12 w-12 mx-auto text-zinc-600 mb-4" />
          <p className="text-[color:var(--text-secondary)]">{error || 'Sem dados disponíveis.'}</p>
        </div>
      </div>
    );
  }

  const { current, hourly, daily, city, alerts } = data;
  const now = Math.floor(Date.now() / 1000);
  const isNight = current.is_day === 0;
  const weatherKind = getWeatherKind(current.weather_code);
  const visKm = (parseInt(String(current.visibility)) / 1000).toFixed(1);

  // Determine background class
  const bgClass = isNight ? 'from-indigo-950/80 via-slate-900/90 to-slate-950' :
    weatherKind === 'rain' || weatherKind === 'storm' ? 'from-slate-800 via-slate-900 to-slate-950' :
    weatherKind === 'cloud' ? 'from-sky-900/60 via-slate-800/80 to-slate-900' :
    'from-sky-500/20 via-blue-600/10 to-slate-900';

  return (
    <div className="h-full overflow-y-auto overflow-x-hidden pb-6 pr-1">
      <div className="flex flex-col gap-5">
        {/* ── Header ── */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-[color:var(--text-primary)]">Clima</h1>
            <p className="text-sm text-[color:var(--text-secondary)] mt-0.5">Condições atuais e previsão estendida.</p>
          </div>
          <div className="flex items-center gap-3">
            <StatusPulse label="Ao vivo" tone="success" />
            <button
              onClick={() => setUnit(unit === 'C' ? 'F' : 'C')}
              className="alfredo-pill border-white/10 bg-white/[0.03] text-[color:var(--text-secondary)] hover:bg-white/[0.06]"
            >
              °{unit === 'C' ? 'F' : 'C'}
            </button>
          </div>
        </div>

        {alerts?.length > 0 && <AlertBanner alerts={alerts} />}

        {/* ── Current Conditions Card ── */}
        <div className={cn(
          'relative overflow-hidden rounded-3xl border border-white/5 p-5 md:p-7',
          'bg-gradient-to-br',
          bgClass,
        )}>
          {/* Background weather icon */}
          <div className="absolute right-2 top-2 opacity-[0.08] pointer-events-none scale-[3] md:scale-[4] origin-top-right">
            <WeatherIconByCode code={current.weather_code} size="lg" isNight={isNight} />
          </div>

          {/* Location + Temp Row */}
          <div className="relative z-10 flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-2 text-sm text-white/70 font-mono mb-3">
                <MapPin className="h-4 w-4 text-rose-400" />
                {city}
              </div>
              <div className="flex items-end gap-4">
                <span className="text-6xl md:text-7xl font-bold text-white leading-none tabular-nums tracking-tighter">
                  {fmtT(current.temperature)}
                </span>
                <div className="flex flex-col pb-1">
                  <span className="text-sm text-white/70">Sensação {fmtT(current.feels_like)}</span>
                  <span className="text-base font-semibold capitalize text-white/90">{current.description}</span>
                </div>
              </div>
              <div className="flex items-center gap-4 mt-4">
                <span className="flex items-center gap-1.5 text-sm text-rose-300">
                  <ArrowUp className="h-4 w-4" /> {fmtT(current.max_temp)}
                </span>
                <span className="flex items-center gap-1.5 text-sm text-sky-300">
                  <ArrowDown className="h-4 w-4" /> {fmtT(current.min_temp)}
                </span>
              </div>
            </div>
            <div className="shrink-0 -mr-2 -mt-2">
              <WeatherIconByCode code={current.weather_code} size="lg" isNight={isNight} />
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="relative z-10 mt-6 grid grid-cols-2 md:grid-cols-4 gap-2">
            <MiniDetail icon={Droplets} label="Umidade" value={`${current.humidity}%`} />
            <MiniDetail icon={Wind} label="Vento" value={`${current.wind_speed} m/s ${windDir(current.wind_deg)}`} />
            <MiniDetail icon={Eye} label="Visibilidade" value={`${visKm} km`} />
            <MiniDetail icon={Gauge} label="Pressão" value={`${current.pressure} hPa`} />
          </div>

          {/* Hourly Forecast */}
          <div className="relative z-10 mt-6">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/50 mb-3">PRÓXIMAS HORAS</h4>
            <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1 snap-x hide-scrollbar">
              {hourly.map((h, i) => (
                <div
                  key={i}
                  className="flex shrink-0 snap-start flex-col items-center gap-1.5 rounded-2xl border border-white/5 bg-white/[0.03] px-3 py-2.5 min-w-[64px]"
                >
                  <span className="text-[10px] font-medium text-white/70">{i === 0 ? 'Agora' : h.time}</span>
                  <WeatherIconByCode code={h.weather_code} size="sm" isNight={h.time < '06:00' || h.time > '18:30'} />
                  <span className="text-[14px] font-bold text-white tabular-nums">{fmtT(h.temp)}</span>
                  {h.pop > 0 && <span className="text-[9px] text-sky-300/70 font-mono">{h.pop}%</span>}
                </div>
              ))}
            </div>
          </div>

          {/* Sun Arc */}
          <div className="relative z-10 mt-6">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/50 mb-3">SOL</h4>
            <SunArc sunrise={current.sunrise} sunset={current.sunset} current={now} />
          </div>
        </div>

        {/* ── 7-Day Forecast ── */}
        <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[color:var(--bg-surface)] p-4 md:p-5">
          <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--text-tertiary)] mb-4">
            PREVISÃO PARA 7 DIAS
          </h4>
          <div className="flex flex-col gap-1.5">
            {daily.map((d, i) => (
              <div
                key={i}
                className="grid grid-cols-[5rem_3rem_1fr_3rem_5rem] md:grid-cols-[6rem_3rem_1fr_3rem_6rem] items-center gap-2 rounded-xl border border-white/5 bg-white/[0.015] px-3 py-2.5 hover:bg-white/[0.03] transition-colors"
              >
                <span className="text-[13px] font-semibold text-[color:var(--text-primary)]">{dayLabel(d.date)}</span>
                <WeatherIconByCode code={d.weather_code} size="sm" />
                <span className="text-[12px] text-[color:var(--text-secondary)] truncate px-1 capitalize">{d.description}</span>
                {d.pop > 0 ? (
                  <span className="text-[11px] text-sky-400/80 font-mono text-right">{d.pop}%</span>
                ) : (
                  <span />
                )}
                <span className="text-[14px] font-bold text-[color:var(--text-primary)] tabular-nums text-right">
                  {fmtT(d.max_temp)} <span className="text-[color:var(--text-tertiary)] font-normal text-[11px]">{fmtT(d.min_temp)}</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
