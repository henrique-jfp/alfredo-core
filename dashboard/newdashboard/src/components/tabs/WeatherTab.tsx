import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../lib/api';
import { ForecastData, WeatherAlert } from '../../types';
import { SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import {
  Droplets, Wind, Eye, Gauge, Sun, Moon,
  ArrowUp, ArrowDown, MapPin, AlertTriangle, CloudRain,
  Activity, CloudFog, Sunrise, Sunset
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
  const s = size === 'lg' ? 'w-24 h-24' : size === 'md' ? 'w-14 h-14' : 'w-8 h-8';

  if (kind === 'sun') return (
    <svg viewBox="0 0 100 100" className={cn("shrink-0", s)}>
      <circle cx="50" cy="50" r="22" className="text-amber-400 fill-amber-400/20" stroke="currentColor" strokeWidth="2" style={{ animation: 'sunPulse 3s infinite' }} />
      <g className="text-amber-400/60" style={{ animation: 'rayRotate 20s linear infinite', transformOrigin: '50% 50%' }}>
        <circle cx="50" cy="50" r="32" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="4 8" />
        <path d="M50 8 L50 15 M50 85 L50 92 M8 50 L15 50 M85 50 L92 50 M20 20 L25 25 M75 75 L80 80 M20 80 L25 75 M75 20 L80 25" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </g>
    </svg>
  );
  if (kind === 'rain') return (
    <svg viewBox="0 0 100 100" className={cn("shrink-0", s)}>
      <g style={{ animation: 'cloudPulse 4s infinite' }}>
        <path d="M25 60 Q10 60 10 45 Q10 30 30 30 Q40 10 60 10 Q80 10 85 30 Q100 30 100 45 Q100 60 85 60 Z" className="text-sky-300 fill-sky-900/40" stroke="currentColor" strokeWidth="2" />
      </g>
      <g className="text-sky-400">
        <line x1="40" y1="65" x2="30" y2="90" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" style={{ animation: 'rainDrop 1s infinite' }} />
        <line x1="60" y1="65" x2="50" y2="90" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" style={{ animation: 'rainDrop 1s infinite 0.3s' }} />
        <line x1="80" y1="65" x2="70" y2="90" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" style={{ animation: 'rainDrop 1s infinite 0.6s' }} />
      </g>
    </svg>
  );
  if (kind === 'storm') return (
    <svg viewBox="0 0 100 100" className={cn("shrink-0", s)}>
      <g style={{ animation: 'cloudPulse 3s infinite' }}>
        <path d="M25 60 Q10 60 10 45 Q10 30 30 30 Q40 10 60 10 Q80 10 85 30 Q100 30 100 45 Q100 60 85 60 Z" className="text-zinc-400 fill-zinc-800/80" stroke="currentColor" strokeWidth="2" />
      </g>
      <g className="text-yellow-400" style={{ animation: 'lightningFlash 4s infinite' }}>
        <path d="M60 45 L45 70 L55 70 L40 95 L70 60 L55 60 Z" fill="currentColor" stroke="currentColor" strokeWidth="1" strokeLinejoin="round" />
      </g>
    </svg>
  );
  if (kind === 'snow') return (
    <svg viewBox="0 0 100 100" className={cn("shrink-0", s)}>
      <g style={{ animation: 'cloudPulse 4s infinite' }}>
        <path d="M25 60 Q10 60 10 45 Q10 30 30 30 Q40 10 60 10 Q80 10 85 30 Q100 30 100 45 Q100 60 85 60 Z" className="text-blue-200 fill-blue-900/30" stroke="currentColor" strokeWidth="2" />
      </g>
      <g className="text-blue-100">
        <path d="M40 70 L40 80 M35 75 L45 75 M37 72 L43 78 M37 78 L43 72" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" style={{ animation: 'snowFall 3s infinite linear', transformOrigin: '40px 75px' }} />
        <path d="M70 65 L70 75 M65 70 L75 70 M67 67 L73 73 M67 73 L73 67" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" style={{ animation: 'snowFall 2.5s infinite linear 1s', transformOrigin: '70px 70px' }} />
      </g>
    </svg>
  );
  
  // Cloud
  return (
    <svg viewBox="0 0 100 100" className={cn("shrink-0", s)}>
      <path d="M30 65 Q20 65 20 55 Q20 45 35 45 Q40 30 55 30 Q70 30 75 45 Q85 45 85 55 Q85 65 75 65 Z" className="text-zinc-500 fill-zinc-500/10" stroke="currentColor" strokeWidth="2" style={{ animation: 'cloudDrift2 8s infinite ease-in-out', transformOrigin: '50% 50%' }} />
      <path d="M25 70 Q10 70 10 55 Q10 40 30 40 Q40 20 60 20 Q80 20 85 40 Q100 40 100 55 Q100 70 85 70 Z" className="text-zinc-300 fill-zinc-300/20" stroke="currentColor" strokeWidth="2.5" style={{ animation: 'cloudDrift 10s infinite ease-in-out', transformOrigin: '50% 50%' }} />
    </svg>
  );
};

const TacticalAlertBanner = ({ alerts }: { alerts: WeatherAlert[] }) => {
  if (!alerts || alerts.length === 0) return null;
  const alert = alerts[0]; 
  
  return (
    <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 md:p-4 backdrop-blur-md shadow-[0_0_15px_rgba(244,63,94,0.15)] flex flex-col md:flex-row gap-3 md:items-center cursor-pointer">
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

const UvGauge = ({ uvi }: { uvi: number }) => {
  const radius = 16;
  const circumference = Math.PI * radius; 
  const maxUv = 11;
  const percent = Math.min(uvi / maxUv, 1);
  const strokeDashoffset = circumference - percent * circumference;
  
  let color = '#a3e635'; 
  if (uvi >= 3) color = '#facc15'; 
  if (uvi >= 6) color = '#fb923c'; 
  if (uvi >= 8) color = '#ef4444'; 
  if (uvi >= 11) color = '#a855f7'; 

  return (
    <div className="relative w-12 h-6 flex items-end justify-center">
      <svg className="w-12 h-6" viewBox="0 0 40 20">
        <path d="M 4 20 A 16 16 0 0 1 36 20" fill="none" stroke="currentColor" strokeWidth="4" className="text-white/10" />
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

const MoonPhaseIcon = ({ phase, size = 'md' }: { phase: number, size?: 'sm'|'md' }) => {
  let iconName = 'Nova';
  if (phase > 0 && phase < 0.25) iconName = 'Cresc.';
  else if (phase === 0.25) iconName = 'Q. Cresc.';
  else if (phase > 0.25 && phase < 0.5) iconName = 'Gib. Cresc.';
  else if (phase === 0.5) iconName = 'Cheia';
  else if (phase > 0.5 && phase < 0.75) iconName = 'Gib. Ming.';
  else if (phase === 0.75) iconName = 'Q. Ming.';
  else if (phase > 0.75 && phase < 1) iconName = 'Ming.';

  const isFullish = phase > 0.3 && phase < 0.7;
  const s = size === 'sm' ? 'w-5 h-5 text-[8px]' : 'w-8 h-8 text-[9px]';

  return (
    <div className="flex flex-col items-center gap-1">
      <div className={cn("rounded-full border border-white/10 shadow-[inset_-6px_0_0_rgba(255,255,255,0.1)] flex items-center justify-center", s,
        isFullish ? "bg-zinc-200" : "bg-zinc-800"
      )}>
        {isFullish && <div className="w-1/3 h-1/3 rounded-full bg-zinc-300 absolute ml-2 mt-2 opacity-50" />}
      </div>
      <span className={cn("text-[color:var(--text-tertiary)] uppercase font-semibold", size === 'sm' ? "text-[8px]" : "text-[9px]")}>{iconName}</span>
    </div>
  );
};

const SunArc = ({ sunrise, sunset, current }: { sunrise: number, sunset: number, current: number }) => {
  const totalDuration = sunset - sunrise;
  const elapsed = current - sunrise;
  let percent = 0;
  
  if (current > sunrise && current < sunset) {
    percent = elapsed / totalDuration;
  } else if (current >= sunset) {
    percent = 1;
  }

  const cx = 10 + (percent * 80); 
  const cy = 40 - Math.sin(percent * Math.PI) * 30;

  return (
    <div className="relative w-full h-12 flex items-center justify-center">
      <svg className="w-full h-12 overflow-visible" viewBox="0 0 100 45" preserveAspectRatio="none">
        <path d="M 10 40 Q 50 -10 90 40" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/10" strokeDasharray="3 4" />
        {(current > sunrise && current < sunset) && (
          <circle cx={cx} cy={cy} r="4" fill="#fbbf24" className="shadow-[0_0_12px_#fbbf24] animate-pulse" />
        )}
      </svg>
      <div className="absolute bottom-0 left-0 text-[10px] text-[color:var(--text-tertiary)] flex justify-between w-full px-1 font-mono">
        <span>{formatUnixTime(sunrise)}</span>
        <span>{formatUnixTime(sunset)}</span>
      </div>
    </div>
  );
};

const MetricCard = ({ icon: Icon, label, value, sub, children }: { icon: any; label: string; value?: React.ReactNode; sub?: string; children?: React.ReactNode }) => (
  <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-3 hover:bg-white/[0.04] transition-colors flex items-center gap-3">
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brass-500/10 border border-brass-500/20 shadow-[0_0_10px_rgba(201,162,75,0.05)]">
      <Icon className="h-4 w-4 text-brass-400" />
    </div>
    <div className="min-w-0 flex-1">
      <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[color:var(--text-tertiary)]">{label}</div>
      {value && <div className="text-[14px] font-bold text-[color:var(--text-primary)] mt-0.5 leading-none tabular-nums">{value}</div>}
      {sub && <div className="text-[10px] text-[color:var(--text-tertiary)] mt-0.5 font-mono">{sub}</div>}
      {children && <div className="mt-1">{children}</div>}
    </div>
  </div>
);

export function WeatherTab() {
  const [data, setData] = useState<ForecastData | null>(null);
  const [error, setError] = useState('');
  const [unit, setUnit] = useState<'C' | 'F'>('C');
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);

  const [expandedDay, setExpandedDay] = useState<number | null>(null);

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
  
  let aqiColor = 'bg-zinc-500';
  let aqiText = 'Desconhecido';
  if (aqi === 1) { aqiColor = 'bg-green-500 shadow-[0_0_8px_#22c55e]'; aqiText = 'Bom'; }
  else if (aqi === 2) { aqiColor = 'bg-yellow-400 shadow-[0_0_8px_#facc15]'; aqiText = 'Razoável'; }
  else if (aqi === 3) { aqiColor = 'bg-orange-500 shadow-[0_0_8px_#f97316]'; aqiText = 'Moderado'; }
  else if (aqi === 4) { aqiColor = 'bg-red-500 shadow-[0_0_8px_#ef4444]'; aqiText = 'Ruim'; }
  else if (aqi === 5) { aqiColor = 'bg-purple-600 shadow-[0_0_8px_#9333ea]'; aqiText = 'Péssimo'; }

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

      {alerts && <TacticalAlertBanner alerts={alerts} />}

      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <div className="flex flex-col gap-4">
          {/* Card Principal Dinâmico */}
          <div className={cn("alfredo-card p-5 md:p-6 overflow-hidden relative border-t-2", bgClass)} style={{ borderTopColor: 'var(--color-brass-500)' }}>
            <div className="relative z-10 flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 text-[12px] text-[color:var(--text-primary)] opacity-80 mb-2 font-mono uppercase tracking-wider">
                  <MapPin className="h-3 w-3 text-brass-400" />
                  {city}
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-7xl font-bold tracking-tighter text-white tabular-nums leading-none drop-shadow-md">
                    {ct(current.temperature)}
                  </span>
                  <div className="flex flex-col items-center">
                    <WeatherIcon code={current.weather_code} size="lg" />
                  </div>
                </div>
                <div className="flex flex-col mt-2">
                    <span className="text-[14px] font-medium text-white/90 capitalize tracking-wide">{current.description}</span>
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
            <MetricCard icon={CloudRain} label="Precipitação" value={`${current.rain?.["1h"] || 0} mm/h`} sub="Última hora" />
            <MetricCard icon={Wind} label="Vel. Vento" value={`${current.wind_speed} m/s`} sub={`Rajada: ${current.wind_gust || 0} m/s • ${getWindDir(current.wind_deg)}`} />
            <MetricCard icon={Activity} label="Qualidade Ar" sub={aqiText}>
              <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden mt-1">
                <div className={cn("h-full transition-all duration-1000", aqiColor)} style={{ width: `${(aqi || 1) * 20}%` }} />
              </div>
            </MetricCard>
            <MetricCard icon={Sun} label="Índice UV">
              <UvGauge uvi={current.uvi || 0} />
            </MetricCard>
            <MetricCard icon={Droplets} label="Pt. Orvalho" value={ct((current.dew_point || 0).toString())} sub={`Umid: ${current.humidity}%`} />
            <MetricCard icon={Gauge} label="Pressão" value={`${current.pressure} hPa`} sub={`Visão: ${visKm} km`} />
          </div>

          {/* Carrossel de Previsão por Hora */}
          <div className="alfredo-card p-4">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--text-tertiary)] mb-3 flex items-center gap-2">
              <CloudFog className="h-3 w-3 text-brass-400" /> Previsão 24h
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
                <div key={i} className="flex shrink-0 flex-col items-center gap-1.5 rounded-xl border border-white/5 bg-white/[0.015] px-3 py-2 min-w-[64px] snap-start hover:bg-white/[0.04] transition-colors select-none">
                  <span className="text-[10px] font-mono font-semibold text-[color:var(--text-tertiary)]">{i === 0 ? 'AGORA' : h.time}</span>
                  <WeatherIcon code={h.weather_code} size="sm" />
                  <span className="text-[14px] font-bold text-[color:var(--text-primary)] tabular-nums">{h.temp}°</span>
                  <div className="flex items-center gap-0.5 text-[10px] text-sky-400/80 font-mono">
                    <Droplets className="h-2.5 w-2.5" /> {h.pop}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          {/* Ciclos Celestes Hoje */}
          <div className="alfredo-card p-4">
             <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--text-tertiary)] mb-4 flex items-center gap-2">
              <Moon className="h-3 w-3 text-brass-400" /> Ciclos Celestes (Hoje)
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

          {/* Previsão Diária Accordion */}
          <div className="alfredo-card p-4 flex-1">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--text-tertiary)] mb-3">
              Projeção 7 Dias
            </h4>
            <div className="space-y-2">
              {daily.slice(0, 7).map((d, i) => {
                const isExpanded = expandedDay === i;
                let durationStr = '--h --m';
                if (d.sunrise && d.sunset) {
                  const diff = d.sunset - d.sunrise;
                  durationStr = `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`;
                }

                return (
                  <div key={i} className="flex flex-col rounded-xl border border-white/5 bg-white/[0.015] hover:border-white/10 hover:bg-white/[0.03] transition-all cursor-pointer" onClick={() => setExpandedDay(isExpanded ? null : i)}>
                    <div className="flex items-center gap-3 px-3 py-2.5">
                      <span className="w-[4.5rem] text-[11px] font-medium text-[color:var(--text-primary)] uppercase tracking-wider">
                        {formatDayName(d.date)}
                      </span>
                      <WeatherIcon code={d.weather_code} size="sm" />
                      <span className="flex-1 text-[11px] text-[color:var(--text-secondary)] truncate pl-2 font-mono">{d.description}</span>
                      {d.pop > 0 && (
                        <span className="text-[10px] text-sky-400/80 font-mono shrink-0 w-8 text-right flex items-center justify-end gap-0.5"><Droplets className="w-2.5 h-2.5"/> {d.pop}%</span>
                      )}
                      <span className="text-[13px] font-bold text-[color:var(--text-primary)] tabular-nums shrink-0 w-16 text-right flex items-center justify-end gap-1.5">
                        {d.max_temp}° <span className="text-[color:var(--text-tertiary)] font-normal text-[10px]">{d.min_temp}°</span>
                      </span>
                    </div>
                    
                    {/* Expanded details */}
                    {isExpanded && (
                      <div className="px-4 pb-3 pt-2 border-t border-white/5 grid grid-cols-3 gap-2 fade-up">
                        <div className="flex flex-col">
                          <span className="text-[9px] uppercase tracking-[0.15em] text-[color:var(--text-tertiary)] flex items-center gap-1"><Sun className="w-2.5 h-2.5 text-brass-400"/> LUZ SOLAR</span>
                          <span className="text-[12px] font-mono font-medium text-amber-400/90 mt-1">{durationStr}</span>
                        </div>
                        <div className="flex flex-col col-span-1">
                          <span className="text-[9px] uppercase tracking-[0.15em] text-[color:var(--text-tertiary)] text-center">NASCER / PÔR</span>
                          <span className="text-[11px] font-mono font-medium text-[color:var(--text-secondary)] mt-1 flex items-center justify-center gap-1.5">
                            {d.sunrise ? formatUnixTime(d.sunrise) : '--:--'} <ArrowDown className="w-2.5 h-2.5 text-zinc-500" /> {d.sunset ? formatUnixTime(d.sunset) : '--:--'}
                          </span>
                        </div>
                        <div className="flex flex-col items-end justify-center">
                          <MoonPhaseIcon phase={d.moon_phase || 0} size="sm" />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}