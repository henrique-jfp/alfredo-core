import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../lib/api';
import { ForecastData, WeatherAlert } from '../../types';
import { SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import {
  Droplets, Wind, Eye, Gauge, Sun, Moon,
  ArrowUp, ArrowDown, MapPin, AlertTriangle, CloudRain,
  Activity, CloudFog
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
  return d.toLocaleDateString('pt-BR', { weekday: 'short' }).replace('-feira', '');
}

function getWindDir(deg: number) {
  const dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  return dirs[Math.round(deg / 22.5) % 16];
}

const WeatherIcon = ({ code, size = 'md' }: { code: number; size?: 'sm' | 'md' | 'lg' }) => {
  const kind = getWeatherKind(code);
  const s = size === 'lg' ? 'w-20 h-20' : size === 'md' ? 'w-12 h-12' : 'w-8 h-8';
  const sInner = size === 'lg' ? 'w-12 h-12' : size === 'md' ? 'w-7 h-7' : 'w-4 h-4';

  if (kind === 'sun') return (
    <div className={cn('relative flex items-center justify-center shrink-0', s)}>
      <div className={cn('absolute inset-0 rounded-full bg-amber-400/20 animate-pulse')} />
      <div className={cn('rounded-full bg-amber-400', sInner)} />
    </div>
  );
  if (kind === 'rain') return (
    <div className={cn('relative flex items-center justify-center shrink-0', s)}>
      <div className={cn('rounded-full bg-sky-400', sInner)} />
      <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 flex gap-0.5">
        <div className="w-0.5 h-1.5 bg-sky-400/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <div className="w-0.5 h-2 bg-sky-400/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <div className="w-0.5 h-1.5 bg-sky-400/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  );
  if (kind === 'storm') return (
    <div className={cn('relative flex items-center justify-center shrink-0', s)}>
      <div className={cn('rounded-full bg-zinc-500', sInner)} />
      <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 text-yellow-300 text-xs font-bold">⚡</div>
    </div>
  );
  if (kind === 'snow') return (
    <div className={cn('relative flex items-center justify-center shrink-0', s)}>
      <div className={cn('rounded-full bg-blue-200', sInner)} />
      <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 text-[10px] text-blue-200">✦</div>
    </div>
  );
  return (
    <div className={cn('relative flex items-center justify-center shrink-0', s)}>
      <div className={cn('rounded-full bg-zinc-400', sInner)} />
    </div>
  );
};

// Componente de Banner Tático
const TacticalAlertBanner = ({ alerts }: { alerts: WeatherAlert[] }) => {
  if (!alerts || alerts.length === 0) return null;
  const alert = alerts[0]; // Mostrar o mais importante
  
  return (
    <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 md:p-4 backdrop-blur-md shadow-[0_0_15px_rgba(244,63,94,0.15)] flex flex-col md:flex-row gap-3 md:items-center">
      <div className="flex items-center gap-2 text-rose-400 font-bold shrink-0">
        <AlertTriangle className="h-5 w-5 animate-pulse" />
        <span className="uppercase tracking-wider text-sm">Alerta Tático</span>
      </div>
      <div className="h-px w-full bg-rose-500/20 md:h-6 md:w-px" />
      <div className="flex-1">
        <h4 className="text-[13px] font-semibold text-rose-300 uppercase">{alert.event}</h4>
        <p className="text-[11px] text-rose-400/80 leading-snug line-clamp-2 md:line-clamp-1">{alert.description}</p>
      </div>
      <div className="text-[10px] font-mono text-rose-500/60 shrink-0 text-right">
        {alert.sender_name}
      </div>
    </div>
  );
};

// Componente de Gauge UV em SVG
const UvGauge = ({ uvi }: { uvi: number }) => {
  const radius = 16;
  const circumference = Math.PI * radius; // Half circle
  const maxUv = 11;
  const percent = Math.min(uvi / maxUv, 1);
  const strokeDashoffset = circumference - percent * circumference;
  
  let color = '#a3e635'; // Low (Green)
  if (uvi >= 3) color = '#facc15'; // Moderate (Yellow)
  if (uvi >= 6) color = '#fb923c'; // High (Orange)
  if (uvi >= 8) color = '#ef4444'; // Very High (Red)
  if (uvi >= 11) color = '#a855f7'; // Extreme (Purple)

  return (
    <div className="relative w-12 h-6 flex items-end justify-center">
      <svg className="w-12 h-6" viewBox="0 0 40 20">
        {/* Track */}
        <path d="M 4 20 A 16 16 0 0 1 36 20" fill="none" stroke="currentColor" strokeWidth="4" className="text-white/10" />
        {/* Fill */}
        <path 
          d="M 4 20 A 16 16 0 0 1 36 20" 
          fill="none" 
          stroke={color} 
          strokeWidth="4" 
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <span className="absolute -bottom-1 text-[11px] font-bold text-white">{uvi.toFixed(1)}</span>
    </div>
  );
};

// Componente de Fase da Lua
const MoonPhaseIcon = ({ phase }: { phase: number }) => {
  // Phase 0 and 1 are new moon, 0.5 is full moon
  let iconName = 'Nova';
  if (phase > 0 && phase < 0.25) iconName = 'Cresc.';
  else if (phase === 0.25) iconName = 'Quart. Cresc.';
  else if (phase > 0.25 && phase < 0.5) iconName = 'Gibosa Cresc.';
  else if (phase === 0.5) iconName = 'Cheia';
  else if (phase > 0.5 && phase < 0.75) iconName = 'Gibosa Ming.';
  else if (phase === 0.75) iconName = 'Quart. Ming.';
  else if (phase > 0.75 && phase < 1) iconName = 'Ming.';

  const isFullish = phase > 0.3 && phase < 0.7;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className={cn("w-8 h-8 rounded-full border border-white/10 shadow-[inset_-6px_0_0_rgba(255,255,255,0.1)] flex items-center justify-center", 
        isFullish ? "bg-zinc-200" : "bg-zinc-800"
      )}>
        {isFullish && <div className="w-3 h-3 rounded-full bg-zinc-300 absolute ml-2 mt-2 opacity-50" />}
      </div>
      <span className="text-[9px] text-[color:var(--text-tertiary)] uppercase font-semibold">{iconName}</span>
    </div>
  );
};

// Componente Arco do Sol
const SunArc = ({ sunrise, sunset, current }: { sunrise: number, sunset: number, current: number }) => {
  const totalDuration = sunset - sunrise;
  const elapsed = current - sunrise;
  let percent = 0;
  
  if (current > sunrise && current < sunset) {
    percent = elapsed / totalDuration;
  } else if (current >= sunset) {
    percent = 1;
  }

  const cx = 10 + (percent * 80); // X pos from 10 to 90
  const cy = 40 - Math.sin(percent * Math.PI) * 30; // Y pos from 40 up to 10 back to 40

  return (
    <div className="relative w-full h-12 flex items-center justify-center">
      <svg className="w-full h-12 overflow-visible" viewBox="0 0 100 45" preserveAspectRatio="none">
        {/* Arc Track */}
        <path d="M 10 40 Q 50 -10 90 40" fill="none" stroke="currentColor" strokeWidth="1" className="text-white/10" strokeDasharray="2 4" />
        
        {/* Sun Dot */}
        {(current > sunrise && current < sunset) && (
          <circle cx={cx} cy={cy} r="4" fill="#fbbf24" className="shadow-[0_0_10px_#fbbf24] animate-pulse" />
        )}
      </svg>
      <div className="absolute bottom-0 left-0 text-[10px] text-[color:var(--text-tertiary)] flex justify-between w-full px-2">
        <span>{formatUnixTime(sunrise)}</span>
        <span>{formatUnixTime(sunset)}</span>
      </div>
    </div>
  );
};

const MetricCard = ({ icon: Icon, label, value, sub, children }: { icon: any; label: string; value?: React.ReactNode; sub?: string; children?: React.ReactNode }) => (
  <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-3 hover:bg-white/[0.04] transition-colors flex items-center gap-3">
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brass-500/10">
      <Icon className="h-4 w-4 text-brass-300" />
    </div>
    <div className="min-w-0 flex-1">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-tertiary)]">{label}</div>
      {value && <div className="text-[14px] font-bold text-[color:var(--text-primary)] mt-0.5 leading-none">{value}</div>}
      {sub && <div className="text-[10px] text-[color:var(--text-tertiary)] mt-0.5">{sub}</div>}
      {children && <div className="mt-1">{children}</div>}
    </div>
  </div>
);

export function WeatherTab() {
  const [data, setData] = useState<ForecastData | null>(null);
  const [error, setError] = useState('');
  const [unit, setUnit] = useState<'C' | 'F'>('C');
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Drag to scroll logic for desktop
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);

  useEffect(() => {
    api.getForecast().then(setData).catch(() => setError('Indisponível'));
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!scrollRef.current) return;
    setIsDragging(true);
    setStartX(e.pageX - scrollRef.current.offsetLeft);
    setScrollLeft(scrollRef.current.scrollLeft);
  };
  const handleMouseLeave = () => setIsDragging(false);
  const handleMouseUp = () => setIsDragging(false);
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !scrollRef.current) return;
    e.preventDefault();
    const x = e.pageX - scrollRef.current.offsetLeft;
    const walk = (x - startX) * 2;
    scrollRef.current.scrollLeft = scrollLeft - walk;
  };

  if (error) {
    return (
      <div className="flex h-full flex-col gap-4 overflow-y-auto pb-safe px-safe">
        <SectionHeading eyebrow="Clima" title="Centro de Comando" subtitle="Monitoramento atmosférico e logístico." />
        <div className="alfredo-card p-8 text-center text-[color:var(--text-tertiary)]">{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-full flex-col gap-4 overflow-y-auto pb-safe px-safe">
        <SectionHeading eyebrow="Clima" title="Centro de Comando" subtitle="Monitoramento atmosférico e logístico." />
        <div className="alfredo-card p-8 text-center text-[color:var(--text-secondary)] text-sm shimmer rounded-2xl h-64 border-none"></div>
      </div>
    );
  }

  const { current, hourly, daily, city, alerts, aqi } = data;
  const ct = (v: string) => unit === 'C' ? `${v}°` : `${Math.round(parseInt(v) * 9 / 5 + 32)}°`;
  const visKm = (parseInt(current.visibility as any) / 1000).toFixed(1);
  const weatherKind = getWeatherKind(current.weather_code);
  const bgClass = `bg-weather-${weatherKind}`;
  
  // AQI color mapping
  let aqiColor = 'bg-zinc-500';
  let aqiText = 'Desconhecido';
  if (aqi === 1) { aqiColor = 'bg-green-500'; aqiText = 'Bom'; }
  else if (aqi === 2) { aqiColor = 'bg-yellow-400'; aqiText = 'Razoável'; }
  else if (aqi === 3) { aqiColor = 'bg-orange-500'; aqiText = 'Moderado'; }
  else if (aqi === 4) { aqiColor = 'bg-red-500'; aqiText = 'Ruim'; }
  else if (aqi === 5) { aqiColor = 'bg-purple-600'; aqiText = 'Péssimo'; }

  const nowUnix = Math.floor(Date.now() / 1000);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto pb-safe px-safe hide-scrollbar">
      <SectionHeading
        eyebrow="Clima"
        title="Centro de Comando"
        subtitle="Monitoramento atmosférico logístico."
        action={
          <div className="flex items-center gap-1.5">
            <StatusPulse label="Ao vivo" tone="success" />
            <button onClick={() => setUnit(unit === 'C' ? 'F' : 'C')} className="alfredo-pill border-white/10 bg-white/[0.03] text-xs text-[color:var(--text-secondary)] px-2">
              °{unit === 'C' ? 'F' : 'C'}
            </button>
          </div>
        }
      />

      {/* Banner Tático */}
      {alerts && <TacticalAlertBanner alerts={alerts} />}

      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <div className="flex flex-col gap-4">
          {/* Card Principal Dinâmico */}
          <div className={cn("alfredo-card p-5 md:p-6 overflow-hidden relative", bgClass)}>
            <div className="relative z-10 flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 text-[12px] text-[color:var(--text-primary)] opacity-80 mb-2 font-mono">
                  <MapPin className="h-3 w-3" />
                  {city}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-7xl font-bold tracking-tighter text-white tabular-nums leading-none">
                    {ct(current.temperature)}
                  </span>
                  <div className="flex flex-col">
                    <WeatherIcon code={current.weather_code} size="md" />
                    <span className="text-[13px] font-medium text-white/90 capitalize mt-1">{current.description}</span>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-4 text-[12px] text-white/70 font-mono">
                  <span>SENS. {ct(current.feels_like)}</span>
                  <span className="flex items-center gap-1"><ArrowUp className="h-3 w-3 text-rose-400" />{ct(current.max_temp)}</span>
                  <span className="flex items-center gap-1"><ArrowDown className="h-3 w-3 text-sky-400" />{ct(current.min_temp)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Grid de Dados Atmosféricos */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <MetricCard icon={CloudRain} label="Volume Chuva" value={`${current.rain?.["1h"] || 0} mm/h`} sub="Última hora" />
            <MetricCard icon={Wind} label="Vento" value={`${current.wind_speed} m/s`} sub={`Rajada: ${current.wind_gust || 0} m/s • ${getWindDir(current.wind_deg)}`} />
            <MetricCard icon={Activity} label="Qualidade do Ar" sub={aqiText}>
              <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden mt-1">
                <div className={cn("h-full", aqiColor)} style={{ width: `${(aqi || 1) * 20}%` }} />
              </div>
            </MetricCard>
            <MetricCard icon={Sun} label="Índice UV">
              <UvGauge uvi={current.uvi || 0} />
            </MetricCard>
            <MetricCard icon={Droplets} label="Ponto Orvalho" value={ct((current.dew_point || 0).toString())} sub={`Umid: ${current.humidity}%`} />
            <MetricCard icon={Gauge} label="Pressão" value={`${current.pressure} hPa`} sub={`Visibilidade: ${visKm} km`} />
          </div>

          {/* Carrossel de Previsão por Hora */}
          <div className="alfredo-card p-4">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--text-tertiary)] mb-3 flex items-center gap-2">
              <CloudFog className="h-3 w-3" /> Linha do Tempo (Próx. 24h)
            </h4>
            <div 
              ref={scrollRef}
              className="flex gap-2 overflow-x-auto pb-1 hide-scrollbar cursor-grab active:cursor-grabbing snap-x"
              onMouseDown={handleMouseDown}
              onMouseLeave={handleMouseLeave}
              onMouseUp={handleMouseUp}
              onMouseMove={handleMouseMove}
            >
              {hourly.slice(0, 24).map((h, i) => (
                <div key={i} className="flex shrink-0 flex-col items-center gap-1.5 rounded-xl border border-white/5 bg-white/[0.015] px-3 py-2 min-w-[64px] snap-start hover:bg-white/[0.03] transition-colors select-none">
                  <span className="text-[10px] font-semibold text-[color:var(--text-tertiary)]">{i === 0 ? 'Agora' : h.time}</span>
                  <WeatherIcon code={h.weather_code} size="sm" />
                  <span className="text-[13px] font-bold text-[color:var(--text-primary)] tabular-nums">{h.temp}°</span>
                  <div className="flex items-center gap-0.5 text-[9px] text-sky-400/80 font-mono">
                    <Droplets className="h-2 w-2" /> {h.pop}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          {/* Ciclos Celestes */}
          <div className="alfredo-card p-4">
             <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--text-tertiary)] mb-4 flex items-center gap-2">
              <Moon className="h-3 w-3" /> Ciclos Celestes
            </h4>
            <div className="flex items-end gap-6 mb-2">
              <div className="flex-1">
                <SunArc sunrise={current.sunrise} sunset={current.sunset} current={nowUnix} />
              </div>
              <div className="shrink-0 pb-1">
                <MoonPhaseIcon phase={daily[0]?.moon_phase || 0} />
              </div>
            </div>
          </div>

          {/* Previsão Diária */}
          <div className="alfredo-card p-4 flex-1">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--text-tertiary)] mb-3">
              Projeção 7 Dias
            </h4>
            <div className="space-y-1.5">
              {daily.slice(0, 7).map((d, i) => (
                <div key={i} className="flex items-center gap-3 rounded-xl border border-transparent hover:border-white/5 hover:bg-white/[0.02] px-2 py-2 transition-colors">
                  <span className="w-[4.5rem] text-[11px] font-medium text-[color:var(--text-primary)] uppercase tracking-wider">
                    {formatDayName(d.date)}
                  </span>
                  <WeatherIcon code={d.weather_code} size="sm" />
                  <span className="flex-1 text-[11px] text-[color:var(--text-secondary)] truncate pl-2">{d.description}</span>
                  {d.pop > 0 && (
                     <span className="text-[10px] text-sky-400/80 font-mono shrink-0 w-8 text-right">{d.pop}%</span>
                  )}
                  <span className="text-[12px] font-semibold text-[color:var(--text-primary)] tabular-nums shrink-0 w-16 text-right">
                    {d.max_temp}° <span className="text-[color:var(--text-tertiary)] font-normal">{d.min_temp}°</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}