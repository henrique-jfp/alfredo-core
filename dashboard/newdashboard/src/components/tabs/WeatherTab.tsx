import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { ForecastData } from '../../types';
import { SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import {
  Droplets, Wind, Eye, Gauge, Sun, Moon,
  ArrowUp, ArrowDown, MapPin
} from 'lucide-react';
import { cn } from '../../lib/utils';

function getWeatherKind(code: number) {
  if (code <= 1) return 'sun';
  if (code <= 3) return 'cloud';
  if (code <= 69 || (code >= 80 && code <= 82)) return 'rain';
  if (code >= 71 && code <= 77) return 'snow';
  if (code >= 95) return 'storm';
  return 'cloud';
}

function uvFromCode(code: number) {
  const kind = getWeatherKind(code);
  if (kind === 'sun') return { level: 'Alto', color: 'text-amber-400' };
  if (kind === 'cloud') return { level: 'Moderado', color: 'text-yellow-400' };
  return { level: 'Baixo', color: 'text-zinc-400' };
}

function getWindDir(deg: number) {
  const dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  return dirs[Math.round(deg / 22.5) % 16];
}

function formatUnixTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function formatDayName(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  if (dateStr === today.toISOString().slice(0, 10)) return 'Hoje';
  if (dateStr === tomorrow.toISOString().slice(0, 10)) return 'Amanhã';
  return d.toLocaleDateString('pt-BR', { weekday: 'long' }).replace('-feira', '');
}

const WeatherIcon = ({ code, size = 'md' }: { code: number; size?: 'sm' | 'md' | 'lg' }) => {
  const kind = getWeatherKind(code);
  const s = size === 'lg' ? 'w-20 h-20' : size === 'md' ? 'w-12 h-12' : 'w-6 h-6';
  const sInner = size === 'lg' ? 'w-12 h-12' : size === 'md' ? 'w-7 h-7' : 'w-3.5 h-3.5';

  if (kind === 'sun') return (
    <div className={cn('relative flex items-center justify-center', s)}>
      <div className={cn('absolute inset-0 rounded-full bg-amber-400/20 animate-pulse')} />
      <div className={cn('rounded-full bg-amber-400', sInner)} />
    </div>
  );
  if (kind === 'rain') return (
    <div className={cn('relative flex items-center justify-center', s)}>
      <div className={cn('rounded-full bg-sky-400', sInner)} />
      <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 flex gap-0.5">
        <div className="w-0.5 h-1.5 bg-sky-400/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <div className="w-0.5 h-2 bg-sky-400/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <div className="w-0.5 h-1.5 bg-sky-400/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  );
  if (kind === 'storm') return (
    <div className={cn('relative flex items-center justify-center', s)}>
      <div className={cn('rounded-full bg-zinc-500', sInner)} />
      <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 text-yellow-300 text-xs">⚡</div>
    </div>
  );
  if (kind === 'snow') return (
    <div className={cn('relative flex items-center justify-center', s)}>
      <div className={cn('rounded-full bg-blue-200', sInner)} />
      <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 text-[10px] text-blue-200">✦</div>
    </div>
  );
  return (
    <div className={cn('relative flex items-center justify-center', s)}>
      <div className={cn('rounded-full bg-zinc-400', sInner)} />
    </div>
  );
};

const MetricCard = ({ icon: Icon, label, value, sub }: { icon: any; label: string; value: string; sub?: string }) => (
  <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-3.5 hover:bg-white/[0.04] transition-colors">
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brass-500/10">
        <Icon className="h-4 w-4 text-brass-300" />
      </div>
      <div className="min-w-0">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-tertiary)]">{label}</div>
        <div className="text-[15px] font-bold text-[color:var(--text-primary)] mt-0.5">{value}</div>
        {sub && <div className="text-[10px] text-[color:var(--text-tertiary)]">{sub}</div>}
      </div>
    </div>
  </div>
);

export function WeatherTab() {
  const [data, setData] = useState<ForecastData | null>(null);
  const [error, setError] = useState('');
  const [unit, setUnit] = useState<'C' | 'F'>('C');

  useEffect(() => {
    api.getForecast().then(setData).catch(() => setError('Indisponível'));
  }, []);

  if (error) {
    return (
      <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
        <SectionHeading eyebrow="Clima" title="Previsão do tempo" subtitle="Detalhes completos do clima." />
        <div className="alfredo-card p-8 text-center text-[color:var(--text-tertiary)]">{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
        <SectionHeading eyebrow="Clima" title="Previsão do tempo" subtitle="Detalhes completos do clima." />
        <div className="alfredo-card p-8 text-center text-[color:var(--text-secondary)] text-sm">Carregando...</div>
      </div>
    );
  }

  const { current, hourly, daily, city } = data;
  const ct = (v: string) => unit === 'C' ? `${v}°C` : `${Math.round(parseInt(v) * 9 / 5 + 32)}°F`;
  const uv = uvFromCode(parseInt(current.weather_code as any));
  const visKm = (parseInt(current.visibility as any) / 1000).toFixed(1);

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pb-10 pr-2">
      <SectionHeading
        eyebrow="Clima"
        title="Previsão do tempo"
        subtitle="Condições atuais e previsão estendida."
        action={
          <div className="flex items-center gap-1.5">
            <StatusPulse label="Ao vivo" tone="success" />
            <button onClick={() => setUnit(unit === 'C' ? 'F' : 'C')} className="alfredo-pill border-white/10 bg-white/[0.03] text-xs text-[color:var(--text-secondary)] px-2">
              °{unit === 'C' ? 'F' : 'C'}
            </button>
          </div>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <div className="alfredo-card p-5 md:p-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 text-[13px] text-[color:var(--text-tertiary)] mb-1">
                <MapPin className="h-3.5 w-3.5" />
                {city}
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-6xl font-bold tracking-tight text-white">
                  {ct(current.temperature)}
                </span>
                <div className="flex flex-col text-[11px] text-[color:var(--text-tertiary)]">
                  <span>Sensação {ct(current.feels_like)}</span>
                  <span>{current.description}</span>
                </div>
              </div>
              <div className="flex items-center gap-3 mt-2 text-[12px] text-[color:var(--text-secondary)]">
                <span className="flex items-center gap-1"><ArrowUp className="h-3 w-3 text-rose-400" /> {ct(current.max_temp)}</span>
                <span className="flex items-center gap-1"><ArrowDown className="h-3 w-3 text-sky-400" /> {ct(current.min_temp)}</span>
              </div>
            </div>
            <WeatherIcon code={parseInt(current.weather_code as any)} size="lg" />
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <MetricCard icon={Droplets} label="Umidade" value={`${current.humidity}%`} />
            <MetricCard icon={Wind} label="Vento" value={`${current.wind_speed} m/s`} sub={getWindDir(current.wind_deg)} />
            <MetricCard icon={Eye} label="Visibilidade" value={`${visKm} km`} />
            <MetricCard icon={Gauge} label="Pressão" value={`${current.pressure} hPa`} sub={uv.level} />
          </div>

          <div className="mt-6">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-tertiary)] mb-3">
              Previsão por hora
            </h4>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {hourly.map((h, i) => (
                <div key={i} className="flex shrink-0 flex-col items-center gap-1.5 rounded-2xl border border-white/5 bg-white/[0.02] px-3 py-2.5 min-w-[68px]">
                  <span className="text-[10px] font-semibold text-[color:var(--text-tertiary)]">{i === 0 ? 'Agora' : h.time}</span>
                  <WeatherIcon code={h.weather_code} size="sm" />
                  <span className="text-[13px] font-bold text-[color:var(--text-primary)]">{h.temp}°</span>
                  <span className="text-[9px] text-[color:var(--text-tertiary)]">{h.pop}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="alfredo-card p-4 md:p-5">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-tertiary)] mb-3">
              Próximos dias
            </h4>
            <div className="space-y-2">
              {daily.slice(0, 5).map((d, i) => (
                <div key={i} className="flex items-center gap-3 rounded-2xl border border-white/5 bg-white/[0.02] px-3 py-2.5">
                  <span className="w-20 text-[12px] font-medium text-[color:var(--text-primary)]">
                    {formatDayName(d.date)}
                  </span>
                  <WeatherIcon code={d.weather_code} size="sm" />
                  <span className="flex-1 text-[11px] text-[color:var(--text-secondary)] truncate">{d.description}</span>
                  <span className="text-[11px] text-[color:var(--text-tertiary)]">{d.pop}%</span>
                  <span className="text-[12px] font-semibold text-[color:var(--text-primary)] tabular-nums">
                    {d.max_temp}° <span className="text-[color:var(--text-tertiary)]">{d.min_temp}°</span>
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="alfredo-card p-4 md:p-5">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--text-tertiary)] mb-3">
              Sol
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <MetricCard icon={Sun} label="Nascer" value={formatUnixTime(parseInt(current.sunrise as any))} />
              <MetricCard icon={Moon} label="Pôr" value={formatUnixTime(parseInt(current.sunset as any))} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}