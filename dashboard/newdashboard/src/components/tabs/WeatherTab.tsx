import React, { useState, useEffect, useRef } from 'react';
import { ForecastData, WeatherAlert, getWeatherKind } from '../../types';
import { SectionHeading, StatusPulse } from '../ui/DashboardPrimitives';
import {
  Droplets, Wind, Eye, Gauge, Sun, Moon,
  ArrowUp, ArrowDown, MapPin, AlertTriangle, CloudRain,
  Activity, CloudFog
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useWeather } from '../../hooks/useWeather';

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

const CountUp = ({ value, duration = 600 }: { value: number, duration?: number }) => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime: number;
    let animationFrame: number;

    const updateCount = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = timestamp - startTime;
      
      if (progress < duration) {
        setCount(Math.round((progress / duration) * value));
        animationFrame = requestAnimationFrame(updateCount);
      } else {
        setCount(value);
      }
    };

    animationFrame = requestAnimationFrame(updateCount);
    return () => cancelAnimationFrame(animationFrame);
  }, [value, duration]);

  return <span>{count}</span>;
};

const WeatherIcon = ({ code, size = 'md', isNight = false }: { code: number; size?: 'sm' | 'md' | 'lg', isNight?: boolean }) => {
  const kind = getWeatherKind(code);
  const s = size === 'lg' ? 'w-24 h-24' : size === 'md' ? 'w-14 h-14' : 'w-8 h-8';

  if (kind === 'sun') {
    if (isNight) {
      return (
        <svg viewBox="0 0 100 100" className={cn("shrink-0", s)}>
          <circle cx="50" cy="50" r="22" className="text-zinc-300 fill-zinc-300/20" stroke="currentColor" strokeWidth="2" style={{ animation: 'sunPulse 4s infinite' }} />
          <path d="M70 40 A 25 25 0 0 0 50 25 A 25 25 0 0 1 50 75 A 25 25 0 0 0 70 60 Z" className="text-zinc-200 fill-zinc-200/50" />
        </svg>
      );
    }
    return (
      <svg viewBox="0 0 100 100" className={cn("shrink-0", s)}>
        <circle cx="50" cy="50" r="22" className="text-amber-400 fill-amber-400/20" stroke="currentColor" strokeWidth="2" style={{ animation: 'sunPulse 3s infinite' }} />
        <g className="text-amber-400/60" style={{ animation: 'rayRotate 20s linear infinite', transformOrigin: '50% 50%' }}>
          <circle cx="50" cy="50" r="32" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="4 8" />
          <path d="M50 8 L50 15 M50 85 L50 92 M8 50 L15 50 M85 50 L92 50 M20 20 L25 25 M75 75 L80 80 M20 80 L25 75 M75 20 L80 25" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </g>
      </svg>
    );
  }
  
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
      {isNight && <circle cx="45" cy="40" r="15" className="text-zinc-300 fill-zinc-300/20" stroke="currentColor" strokeWidth="1" />}
      <path d="M30 65 Q20 65 20 55 Q20 45 35 45 Q40 30 55 30 Q70 30 75 45 Q85 45 85 55 Q85 65 75 65 Z" className="text-zinc-500 fill-zinc-500/10" stroke="currentColor" strokeWidth="2" style={{ animation: 'cloudDrift2 8s infinite ease-in-out', transformOrigin: '50% 50%' }} />
      <path d="M25 70 Q10 70 10 55 Q10 40 30 40 Q40 20 60 20 Q80 20 85 40 Q100 40 100 55 Q100 70 85 70 Z" className="text-zinc-300 fill-zinc-300/20" stroke="currentColor" strokeWidth="2.5" style={{ animation: 'cloudDrift 10s infinite ease-in-out', transformOrigin: '50% 50%' }} />
    </svg>
  );
};

const TacticalAlertBanner = ({ alerts }: { alerts: WeatherAlert[] }) => {
  if (!alerts || alerts.length === 0) return null;
  const alert = alerts[0]; 
  
  return (
    <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 md:p-4 backdrop-blur-md shadow-[0_0_15px_rgba(244,63,94,0.15)] flex flex-col md:flex-row gap-3 md:items-center cursor-pointer hover:-translate-y-0.5 transition-transform">
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
      <div className={cn("rounded-full border border-white/10 shadow-[inset_-6px_0_0_rgba(255,255,255,0.1)] flex items-center justify-center relative overflow-hidden", s,
        isFullish ? "bg-zinc-200" : "bg-zinc-800"
      )}>
        {isFullish && <div className="w-full h-full rounded-full bg-black/40 absolute left-1/3 mix-blend-multiply" />}
      </div>
      <span className={cn("text-[color:var(--text-tertiary)] uppercase font-semibold", size === 'sm' ? "text-[8px]" : "text-[9px]")}>{iconName}</span>
    </div>
  );
};

const SunArc = ({ sunrise, sunset, current, isNight, moonrise, moonset }: { sunrise: number, sunset: number, current: number, isNight: boolean, moonrise?: number, moonset?: number }) => {
  
  let start = sunrise;
  let end = sunset;
  let isMoon = false;
  
  // Se for noite e tivermos os dados da lua, faremos o arco lunar
  if (isNight && moonrise && moonset) {
    start = moonrise;
    end = moonset;
    isMoon = true;
    
    // Se moonset for antes do moonrise (cruzou meia noite), ajustamos
    if (end < start && current < end) {
      start -= 86400; // moonrise de ontem
    } else if (end < start && current > start) {
      end += 86400; // moonset de amanha
    }
  }

  const totalDuration = end - start;
  const elapsed = current - start;
  let percent = 0;
  
  if (current > start && current < end) {
    percent = elapsed / totalDuration;
  } else if (current >= end) {
    percent = 1;
  }

  const cx = 10 + (percent * 80); 
  const cy = 40 - Math.sin(percent * Math.PI) * 30;

  return (
    <div className="relative w-full h-12 flex items-center justify-center">
      <svg className="w-full h-12 overflow-visible" viewBox="0 0 100 45" preserveAspectRatio="none">
        <path d="M 10 40 Q 50 -10 90 40" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/10" strokeDasharray="3 4" />
        {(current > start && current < end) && (
          <circle cx={cx} cy={cy} r="4" fill={isMoon ? "#e4e4e7" : "#fbbf24"} className={isMoon ? "shadow-[0_0_12px_#e4e4e7] animate-pulse" : "shadow-[0_0_12px_#fbbf24] animate-pulse"} />
        )}
      </svg>
      <div className="absolute bottom-0 left-0 text-[10px] text-[color:var(--text-tertiary)] flex justify-between w-full px-1 font-mono">
        <span>{formatUnixTime(start)}</span>
        <span>{formatUnixTime(end)}</span>
      </div>
    </div>
  );
};const WeatherMetricCard = ({ icon: Icon, label, value, sub }: { icon: React.ComponentType<{ className?: string }>; label: string; value?: React.ReactNode; sub?: string }) => (
  <div className="glass-panel p-4 flex flex-col md:flex-row items-start md:items-center gap-3 w-full">
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white/10 text-white/90 shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]">
      <Icon className="h-5 w-5 drop-shadow-md" />
    </div>
    <div className="min-w-0 flex-1">
      <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-white/60">{label}</div>
      {value && <div className="text-[16px] font-bold text-white mt-1 leading-none tabular-nums drop-shadow-md">{value}</div>}
      {sub && <div className="text-[11px] text-white/50 mt-1 font-mono uppercase tracking-wider">{sub}</div>}
    </div>
  </div>
);

export function WeatherTab() {
  const { data, loading, error } = useWeather();
  const [unit, setUnit] = useState<'C' | 'F'>('C');
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);

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

  if (loading) {
    return (
      <div className="flex h-full flex-col gap-4 overflow-hidden rounded-3xl bg-zinc-900 pb-safe px-safe relative">
        <div className="absolute inset-0 z-0 bg-cover bg-center opacity-20" style={{ backgroundImage: 'url("https://images.unsplash.com/photo-1483729558449-99ef09a8c325?q=80&w=2070&auto=format&fit=crop")' }} />
        <div className="relative z-10 p-8 flex justify-center items-center h-full">
          <div className="glass-deep p-8 w-full max-w-lg text-center shimmer h-64 border-none" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex h-full flex-col gap-4 overflow-hidden rounded-3xl bg-zinc-900 pb-safe px-safe relative">
        <div className="absolute inset-0 z-0 bg-cover bg-center opacity-20" style={{ backgroundImage: 'url("https://images.unsplash.com/photo-1483729558449-99ef09a8c325?q=80&w=2070&auto=format&fit=crop")' }} />
        <div className="relative z-10 p-8 flex justify-center items-center h-full">
          <div className="glass-deep p-8 w-full max-w-lg text-center text-white/50">{error || 'Sem dados atmosféricos.'}</div>
        </div>
      </div>
    );
  }

  const { current, hourly, daily, city, alerts } = data;
  
  const parseTemp = (v: string) => {
    const n = parseInt(v);
    return unit === 'C' ? n : Math.round(n * 9 / 5 + 32);
  };
  const ctf = (v: string) => `${parseTemp(v)}°`;
  const visKm = (parseInt(current.visibility as any) / 1000).toFixed(1);
  const weatherKind = getWeatherKind(current.weather_code);
  const nowUnix = Math.floor(Date.now() / 1000);
  const isNight = current.is_day === 0;

  let photoOverlayClass = 'bg-weather-photo-day';
  if (weatherKind === 'rain' || weatherKind === 'snow') photoOverlayClass = 'bg-weather-photo-rain';
  else if (weatherKind === 'storm') photoOverlayClass = 'bg-weather-photo-storm';
  else if (weatherKind === 'cloud') photoOverlayClass = 'bg-weather-photo-cloud';
  else {
    if (isNight) photoOverlayClass = 'bg-weather-photo-night';
    else {
      const nearSunrise = Math.abs(nowUnix - current.sunrise) < 3600 * 1.5;
      const nearSunset = Math.abs(nowUnix - current.sunset) < 3600 * 1.5;
      photoOverlayClass = (nearSunrise || nearSunset) ? 'bg-weather-photo-sunset' : 'bg-weather-photo-day';
    }
  }

  return (
    <div className="relative flex h-full flex-col overflow-y-auto hide-scrollbar rounded-3xl overflow-hidden bg-obsidian-900 shadow-2xl">
      <div 
        className="absolute inset-0 z-0 bg-cover bg-center bg-no-repeat transition-all duration-1000"
        style={{ backgroundImage: 'url("https://images.unsplash.com/photo-1483729558449-99ef09a8c325?q=80&w=2070&auto=format&fit=crop")' }}
      >
        <div className={cn("absolute inset-0 transition-colors duration-1000", photoOverlayClass)} />
        {isNight && <div className="absolute inset-0 parallax-stars opacity-80" />}
        {(weatherKind === 'rain' || weatherKind === 'storm') && <div className="absolute inset-0 bg-black/20" />}
      </div>

      <div className="relative z-10 p-4 md:p-8 flex flex-col gap-6 md:gap-8 min-h-max text-white">
        
        {/* Header Superior */}
        <div className="flex items-start justify-between">
           <div className="flex flex-col drop-shadow-md">
             <span className="text-[10px] uppercase tracking-[0.2em] text-white/70 font-bold mb-1">CLIMA</span>
             <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-white">Previsão do tempo</h1>
             <p className="text-sm text-white/70 mt-1 hidden md:block">Condições atuais e previsão estendida.</p>
           </div>
           <div className="flex items-center gap-3">
              <StatusPulse label="Ao vivo" tone="success" />
              <button onClick={() => setUnit(unit === 'C' ? 'F' : 'C')} className="glass-deep border-none px-3 py-1.5 text-xs hover:bg-white/10 text-white font-bold tracking-widest shadow-none">
                °{unit === 'C' ? 'F' : 'C'}
              </button>
           </div>
        </div>

        {alerts && alerts.length > 0 && <TacticalAlertBanner alerts={alerts} />}

        {/* Layout Principal em Grid responsivo. 
            Em telas muito grandes: 1.5fr / 1fr. 
            Em telas médias (md): 1fr / 1fr (2 colunas iguais) 
            Em telas pequenas: 1 coluna */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[1.5fr_1fr] gap-6 lg:gap-8 pb-8">
           
           {/* Coluna Esquerda: Métricas Atuais */}
           <div className="flex flex-col gap-6 lg:gap-8">
              
              <div className="glass-deep p-6 md:p-8 flex flex-col gap-8 relative overflow-hidden">
                 
                 <div className="flex justify-between items-start drop-shadow-md relative z-10">
                    <div className="flex flex-col">
                       <div className="flex items-center gap-2 text-sm text-white/80 font-mono uppercase tracking-widest mb-4">
                         <MapPin className="h-4 w-4 text-rose-400" /> {city}
                       </div>
                       <div className="flex items-end gap-4">
                         <span className="text-7xl md:text-8xl font-bold tracking-tighter text-white tabular-nums leading-none">
                           <CountUp value={parseTemp(current.temperature)} />°C
                         </span>
                         <div className="flex flex-col pb-3">
                           <span className="text-sm font-medium text-white/80">Sensação {ctf(current.feels_like)}</span>
                           <span className="text-base font-semibold capitalize text-white/90">{current.description}</span>
                         </div>
                       </div>
                       <div className="flex items-center gap-5 mt-5 text-base font-semibold text-white/80">
                         <span className="flex items-center gap-1.5 text-rose-300 drop-shadow-sm"><ArrowUp className="h-5 w-5" /> {ctf(current.max_temp)}</span>
                         <span className="flex items-center gap-1.5 text-sky-300 drop-shadow-sm"><ArrowDown className="h-5 w-5" /> {ctf(current.min_temp)}</span>
                       </div>
                    </div>
                 </div>

                 <div className="absolute top-0 right-0 opacity-80 pointer-events-none scale-125 md:scale-150 transform-gpu blur-[1px] translate-x-4 -translate-y-4 md:-translate-y-8">
                   <WeatherIcon code={current.weather_code} size="lg" isNight={isNight} />
                 </div>

                 <div className="flex flex-col gap-6 relative z-10 mt-4">
                   {/* Métricas Rápidas (2x2 em mobile, 4 em linha no desktop) */}
                    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
                       <WeatherMetricCard icon={Droplets} label="Umidade" value={`${current.humidity}%`} />
                       <WeatherMetricCard icon={Wind} label="Vento" value={`${current.wind_speed} m/s`} sub={getWindDir(current.wind_deg)} />
                       <WeatherMetricCard icon={Eye} label="Visibilidade" value={`${visKm} km`} />
                       <WeatherMetricCard icon={Gauge} label="Pressão" value={`${current.pressure} hPa`} sub={Number(current.pressure) < 1010 ? "Baixo" : "Normal"} />
                    </div>

                   {/* Previsão por Hora */}
                   <div className="flex flex-col gap-3 mt-2">
                      <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/50 drop-shadow-sm">PREVISÃO POR HORA</h4>
                      <div 
                        ref={scrollRef}
                        className="flex gap-3 overflow-x-auto pb-3 pt-1 px-1 hide-scrollbar cursor-grab active:cursor-grabbing snap-x -mx-1"
                        onMouseDown={handleMouseDown} onMouseLeave={handleMouseLeave} onMouseUp={handleMouseUp} onMouseMove={handleMouseMove}
                      >
                         {hourly.map((h, i) => (
                           <div key={i} className="glass-panel px-4 py-3 shrink-0 flex flex-col items-center gap-2.5 min-w-[72px] md:min-w-[80px] snap-start glass-panel-hover border-none">
                             <span className="text-[11px] font-medium text-white/80">{i===0 ? 'Agora' : h.time}</span>
                             <div className="drop-shadow-md"><WeatherIcon code={h.weather_code} size="sm" isNight={h.time < "06:00" || h.time > "18:30"} /></div>
                             <span className="text-[16px] font-bold tabular-nums drop-shadow-md"><CountUp value={parseTemp(h.temp.toString())} />°</span>
                             <span className="text-[10px] font-mono text-sky-200/80 mt-1">{h.pop}%</span>
                           </div>
                         ))}
                      </div>
                   </div>
                 </div>
              </div>
           </div>

           {/* Coluna Direita: Próximos dias e Sol */}
           <div className="flex flex-col gap-6 lg:gap-8 relative">
              
              <div className="glass-deep p-6 flex flex-col z-10 relative">
                 <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/50 mb-5 drop-shadow-sm">PRÓXIMOS DIAS</h4>
                 <div className="flex flex-col gap-2">
                    {daily.slice(0, 5).map((d, i) => (
                       <div key={i} className="glass-panel flex items-center gap-3 px-4 py-3 glass-panel-hover shadow-sm border-none">
                          <span className="w-16 md:w-20 text-[13px] font-medium text-white/90 drop-shadow-sm">{formatDayName(d.date)}</span>
                          <div className="drop-shadow-md"><WeatherIcon code={d.weather_code} size="sm" /></div>
                          <span className="flex-1 text-[12px] text-white/70 truncate pl-2 font-medium capitalize">{d.description}</span>
                          {d.pop > 0 && <span className="text-[11px] text-sky-300/80 font-mono w-8 text-right drop-shadow-sm">{d.pop}%</span>}
                          <span className="text-[14px] font-bold text-white tabular-nums w-16 text-right flex justify-end gap-1.5 drop-shadow-md">
                             {ctf(d.max_temp.toString())} <span className="text-white/40 font-normal text-[11px]">{ctf(d.min_temp.toString())}</span>
                          </span>
                       </div>
                    ))}
                 </div>
              </div>

              <div className="glass-deep p-6 border-white/20 shadow-[inset_0_1px_0_rgba(255,255,255,0.4)] relative overflow-hidden h-40 shrink-0">
                 <div className="absolute inset-0 bg-gradient-to-t from-orange-600/30 via-purple-800/40 to-transparent mix-blend-overlay" />
                 <div className="absolute inset-0 bg-gradient-to-r from-indigo-900/40 to-rose-900/30" />
                 
                 <div className="relative z-10 flex flex-col h-full justify-between">
                   <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/70 drop-shadow-sm mb-2">SOL</h4>
                   <div className="mt-auto drop-shadow-lg scale-105 transform origin-bottom">
                     <SunArc 
                       sunrise={current.sunrise} 
                       sunset={current.sunset} 
                       current={nowUnix} 
                       isNight={isNight}
                     />
                   </div>
                 </div>
                 
                 <div className="absolute bottom-4 left-6 right-6 flex justify-between items-end">
                    <div className="flex flex-col text-left drop-shadow-md">
                      <span className="text-[8px] uppercase tracking-[0.2em] text-white/60 font-bold mb-0.5">NASCER</span>
                      <span className="text-[13px] font-bold font-mono text-white/90">{formatUnixTime(current.sunrise)}</span>
                    </div>
                    <div className="flex flex-col text-right drop-shadow-md">
                      <span className="text-[8px] uppercase tracking-[0.2em] text-white/60 font-bold mb-0.5">PÔR</span>
                      <span className="text-[13px] font-bold font-mono text-white/90">{formatUnixTime(current.sunset)}</span>
                    </div>
                 </div>
              </div>

           </div>
        </div>
      </div>
    </div>
  );
}