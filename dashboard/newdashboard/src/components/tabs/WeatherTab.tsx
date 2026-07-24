import React, { useId, useMemo } from 'react';
import { cn } from '../lib/utils';

type WeatherKind = 'sun' | 'cloud' | 'rain' | 'snow' | 'storm';

export type WeatherIconSize = 'sm' | 'md' | 'lg' | 'xl';

interface WeatherIconProps {
  kind: WeatherKind;
  size?: WeatherIconSize;
  isNight?: boolean;
  className?: string;
}

const sizeMap: Record<WeatherIconSize, number> = {
  sm: 48,
  md: 72,
  lg: 120,
  xl: 160,
};

// ─── Sun (clear sky, day) ──────────────────────────────────────────────────

function SunSVG({ w }: { w: number }) {
  const id = useId();
  const s = w / 100; // scale factor
  return (
    <svg viewBox="0 0 100 100" width={w} height={w} className="drop-shadow-md overflow-visible">
      <defs>
        <radialGradient id={`${id}-grad`} cx="40%" cy="35%" r="60%">
          <stop offset="0%" stopColor="#fffbe6" />
          <stop offset="25%" stopColor="#ffe066" />
          <stop offset="55%" stopColor="#ffb300" />
          <stop offset="85%" stopColor="#ff8f00" />
          <stop offset="100%" stopColor="#e65100" />
        </radialGradient>
        <radialGradient id={`${id}-glow`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgba(255,200,50,0.4)" />
          <stop offset="55%" stopColor="rgba(255,180,40,0.12)" />
          <stop offset="100%" stopColor="rgba(255,180,40,0)" />
        </radialGradient>
        <filter id={`${id}-blur`}>
          <feGaussianBlur stdDeviation={2 * s} />
        </filter>
      </defs>
      {/* Outer glow */}
      <circle cx="50" cy="50" r="48" fill={`url(#${id}-glow)`}>
        <animate attributeName="r" values="46;51;46" dur="3s" repeatCount="indefinite" />
      </circle>
      {/* Rays — inner ring, bold */}
      <g>
        <animateTransform attributeName="transform" type="rotate" from="0 50 50" to="360 50 50" dur="40s" repeatCount="indefinite" />
        {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map((angle) => (
          <line
            key={`inner-${angle}`}
            x1="50" y1="10"
            x2="50" y2="19"
            stroke="rgba(255,200,50,0.55)"
            strokeWidth={1.6 * s}
            strokeLinecap="round"
            transform={`rotate(${angle} 50 50)`}
            filter={`url(#${id}-blur)`}
          />
        ))}
        {/* Rays — outer ring, fine, offset for a starburst feel */}
        {[15, 75, 135, 195, 255, 315].map((angle) => (
          <line
            key={`outer-${angle}`}
            x1="50" y1="4"
            x2="50" y2="10"
            stroke="rgba(255,220,120,0.35)"
            strokeWidth={1 * s}
            strokeLinecap="round"
            transform={`rotate(${angle} 50 50)`}
          />
        ))}
      </g>
      {/* Sun body */}
      <circle cx="50" cy="50" r="22" fill={`url(#${id}-grad)`}>
        <animate attributeName="r" values="21;23.5;21" dur="3s" repeatCount="indefinite" />
      </circle>
      {/* Surface highlight */}
      <ellipse cx="40" cy="40" rx="8" ry="6" fill="rgba(255,255,255,0.35)" transform="rotate(-20 40 40)" />
    </svg>
  );
}

// ─── Cloud (overcast) ──────────────────────────────────────────────────────

function CloudSVG({ w, color = '#9ca3af', dark = false }: { w: number; color?: string; dark?: boolean }) {
  const id = useId();
  const c = dark ? '#2d2d3a' : color;
  return (
    <svg viewBox="0 0 100 60" width={w} height={w * 0.6} className="overflow-visible">
      <defs>
        <filter id={`${id}-shadow`}>
          <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="rgba(0,0,0,0.25)" />
        </filter>
      </defs>
      <g filter={`url(#${id}-shadow)`}>
        {/* Bottom base */}
        <ellipse cx="50" cy="48" rx="48" ry="14" fill={c} opacity="0.9" />
        {/* Main bumps */}
        <ellipse cx="30" cy="36" rx="24" ry="20" fill={c} />
        <ellipse cx="70" cy="38" rx="22" ry="18" fill={c} />
        {/* Top bumps */}
        <ellipse cx="45" cy="26" rx="20" ry="18" fill={c} />
        <ellipse cx="62" cy="28" rx="16" ry="15" fill={c} />
        <ellipse cx="28" cy="32" rx="14" ry="12" fill={c} />
        {/* Rim light */}
        <ellipse cx="40" cy="22" rx="10" ry="6" fill="rgba(255,255,255,0.12)" />
      </g>
    </svg>
  );
}

// ─── Sun + Clouds (partly cloudy) ──────────────────────────────────────────

function CloudSunSVG({ w }: { w: number }) {
  const s = w / 100;
  return (
    <svg viewBox="0 0 100 80" width={w} height={w * 0.8} className="overflow-visible">
      {/* Sun behind clouds */}
      <g transform="translate(28, 10)">
        <circle cx="30" cy="30" r="16" fill="#ffb300" opacity="0.75">
          <animate attributeName="r" values="15;17;15" dur="3s" repeatCount="indefinite" />
        </circle>
        <circle cx="30" cy="30" r="20" fill="rgba(255,200,50,0.18)">
          <animate attributeName="r" values="18;23;18" dur="3s" repeatCount="indefinite" />
        </circle>
        {/* Soft rays */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <line key={a} x1="30" y1="10" x2="30" y2="14" stroke="rgba(255,200,50,0.28)" strokeWidth={2 * s} strokeLinecap="round" transform={`rotate(${a} 30 30)`}>
            <animateTransform attributeName="transform" type="rotate" from={`${a} 30 30`} to={`${a + 360} 30 30`} dur="40s" repeatCount="indefinite" />
          </line>
        ))}
      </g>
      {/* Front clouds (drifting) */}
      <g transform="translate(6, 30)">
        <animateTransform attributeName="transform" type="translate" values="6,30;14,30;6,30" dur="14s" repeatCount="indefinite" />
        <CloudSVG w={w * 0.8} color="#9ca3af" />
      </g>
      <g>
        <ellipse cx="60" cy="52" rx="28" ry="14" fill="#b0b8c4" opacity="0.7">
          <animateTransform attributeName="transform" type="translate" values="0,0;-5,0;0,0" dur="10s" repeatCount="indefinite" />
        </ellipse>
      </g>
    </svg>
  );
}

// ─── Rain ──────────────────────────────────────────────────────────────────

const RAIN_DROPS = [
  { x: 20, delay: 0 }, { x: 30, delay: 0.15 }, { x: 42, delay: 0.3 },
  { x: 55, delay: 0.1 }, { x: 65, delay: 0.4 }, { x: 75, delay: 0.2 },
  { x: 85, delay: 0.35 }, { x: 25, delay: 0.5 }, { x: 48, delay: 0.45 },
  { x: 60, delay: 0.55 }, { x: 35, delay: 0.6 }, { x: 70, delay: 0.65 },
  { x: 80, delay: 0.25 }, { x: 15, delay: 0.7 },
];

function RainSVG({ w, isNight = false }: { w: number; isNight?: boolean }) {
  const s = w / 100;
  return (
    <svg viewBox="0 0 100 100" width={w} height={w} className="overflow-visible">
      {/* Cloud */}
      <g transform="translate(0, 5)">
        <CloudSVG w={w * 0.9} color={isNight ? '#232838' : '#2d3748'} dark />
      </g>
      {/* Rain streaks with stagger */}
      {RAIN_DROPS.map(({ x, delay }) => (
        <line
          key={`rain-${x}-${delay}`}
          x1={x} y1="50" x2={x - 4} y2="90"
          stroke="rgba(148,163,184,0.5)"
          strokeWidth={1.5 * s}
          strokeLinecap="round"
        >
          <animate attributeName="y1" values="45;55;45" dur={`${0.5 + delay * 0.2}s`} begin={`${delay}s`} repeatCount="indefinite" />
          <animate attributeName="y2" values="85;95;85" dur={`${0.5 + delay * 0.2}s`} begin={`${delay}s`} repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.3;0.7;0.3" dur={`${0.5 + delay * 0.2}s`} begin={`${delay}s`} repeatCount="indefinite" />
        </line>
      ))}
      {/* Splash puddles */}
      <g opacity="0.2">
        <ellipse cx="30" cy="92" rx="8" ry="2" fill="#94a3b8" />
        <ellipse cx="60" cy="94" rx="10" ry="2.5" fill="#94a3b8" />
        <ellipse cx="80" cy="91" rx="6" ry="1.5" fill="#94a3b8" />
      </g>
    </svg>
  );
}

// ─── Storm ─────────────────────────────────────────────────────────────────

const STORM_DROPS = [
  { x: 15, d: 0 }, { x: 25, d: 0.1 }, { x: 35, d: 0.2 }, { x: 45, d: 0.05 },
  { x: 55, d: 0.3 }, { x: 65, d: 0.15 }, { x: 75, d: 0.25 }, { x: 85, d: 0.35 },
  { x: 20, d: 0.4 }, { x: 40, d: 0.45 }, { x: 60, d: 0.5 }, { x: 80, d: 0.3 },
];

function StormSVG({ w, isNight = false }: { w: number; isNight?: boolean }) {
  const id = useId();
  return (
    <svg viewBox="0 0 100 100" width={w} height={w} className="overflow-visible">
      <defs>
        <filter id={`${id}-flash`}>
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {/* Very dark cloud */}
      <g transform="translate(0, 5)">
        <CloudSVG w={w * 0.95} color={isNight ? '#131320' : '#1a1a28'} dark />
      </g>
      {/* Flash background */}
      <rect x="0" y="0" width="100" height="100" fill="rgba(255,250,210,0.08)" rx="50%">
        <animate attributeName="opacity" values="0;0;0;0;0.6;0;0;0;0;0;0;0.4;0;0" dur="4s" repeatCount="indefinite" />
      </rect>
      {/* Main lightning bolt */}
      <g filter={`url(#${id}-flash)`}>
        <polygon points="55,32 40,55 50,55 38,82 65,50 52,50 60,32" fill="#fff8e1" opacity="0.95">
          <animate attributeName="opacity" values="0;0;0;0;1;0;0;0;0;0;0;0.8;0;0" dur="4s" repeatCount="indefinite" />
        </polygon>
      </g>
      {/* Secondary bolt */}
      <g filter={`url(#${id}-flash)`}>
        <polygon points="35,28 25,48 32,48 22,70 42,46 34,46 40,28" fill="#fff8e1" opacity="0.7">
          <animate attributeName="opacity" values="0;0;0;0;0;0;0;0;0;0;0.9;0;0;0" dur="4s" repeatCount="indefinite" />
        </polygon>
      </g>
      {/* Rain */}
      {STORM_DROPS.map(({ x, d }) => (
        <line
          key={`storm-rain-${x}-${d}`}
          x1={x} y1="48" x2={x - 3} y2="88"
          stroke="rgba(148,163,184,0.4)"
          strokeWidth={1.5}
          strokeLinecap="round"
        >
          <animate attributeName="y1" values="44;52;44" dur="0.4s" begin={`${d}s`} repeatCount="indefinite" />
          <animate attributeName="y2" values="84;92;84" dur="0.4s" begin={`${d}s`} repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.2;0.6;0.2" dur="0.4s" begin={`${d}s`} repeatCount="indefinite" />
        </line>
      ))}
    </svg>
  );
}

// ─── Snow ──────────────────────────────────────────────────────────────────

// Deterministic sway direction/duration per flake — no Math.random() at render time.
const SNOW_FLAKES = [
  { cx: 20, delay: 0, sway: 6, dur: 2.0 }, { cx: 35, delay: 0.5, sway: -5, dur: 2.6 },
  { cx: 50, delay: 1.0, sway: 7, dur: 2.3 }, { cx: 65, delay: 0.3, sway: -6, dur: 2.8 },
  { cx: 80, delay: 0.8, sway: 5, dur: 2.1 }, { cx: 28, delay: 1.5, sway: -7, dur: 2.9 },
  { cx: 45, delay: 0.7, sway: 6, dur: 2.4 }, { cx: 72, delay: 1.2, sway: -5, dur: 2.2 },
  { cx: 55, delay: 0.4, sway: 7, dur: 2.7 }, { cx: 15, delay: 1.8, sway: -6, dur: 2.5 },
  { cx: 40, delay: 0.9, sway: 5, dur: 2.6 }, { cx: 75, delay: 1.6, sway: -7, dur: 2.3 },
];

function SnowSVG({ w, isNight = false }: { w: number; isNight?: boolean }) {
  return (
    <svg viewBox="0 0 100 100" width={w} height={w} className="overflow-visible">
      <g transform="translate(0, 5)">
        <CloudSVG w={w * 0.85} color={isNight ? '#566172' : '#6b7b8d'} />
      </g>
      {SNOW_FLAKES.map(({ cx, delay, sway, dur }) => (
        <circle key={`snow-${cx}-${delay}`} cx={cx} cy="50" r="1.8" fill="white" opacity="0.8">
          <animate attributeName="cy" values="45;95" dur={`${dur}s`} begin={`${delay}s`} repeatCount="indefinite" />
          <animate attributeName="cx" values={`${cx};${cx + sway};${cx}`} dur={`${dur + 0.3}s`} begin={`${delay}s`} repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.9;0.6;0" dur={`${dur}s`} begin={`${delay}s`} repeatCount="indefinite" />
        </circle>
      ))}
    </svg>
  );
}

// ─── Moon (night clear) ────────────────────────────────────────────────────

function MoonSVG({ w }: { w: number }) {
  const id = useId();
  return (
    <svg viewBox="0 0 100 100" width={w} height={w} className="overflow-visible">
      <defs>
        <radialGradient id={`${id}-grad`}>
          <stop offset="0%" stopColor="#f0f0f5" />
          <stop offset="100%" stopColor="#c4c4d0" />
        </radialGradient>
      </defs>
      {/* Twinkling stars */}
      <circle cx="82" cy="22" r="1.2" fill="white">
        <animate attributeName="opacity" values="0.3;1;0.3" dur="2.2s" repeatCount="indefinite" />
      </circle>
      <circle cx="18" cy="72" r="1" fill="white">
        <animate attributeName="opacity" values="1;0.3;1" dur="2.6s" repeatCount="indefinite" />
      </circle>
      <circle cx="24" cy="28" r="0.9" fill="white">
        <animate attributeName="opacity" values="0.4;1;0.4" dur="1.8s" repeatCount="indefinite" />
      </circle>
      {/* Soft glow */}
      <circle cx="50" cy="50" r="24" fill="rgba(200,200,230,0.15)">
        <animate attributeName="r" values="22;26;22" dur="4s" repeatCount="indefinite" />
      </circle>
      {/* Moon body */}
      <circle cx="50" cy="50" r="22" fill={`url(#${id}-grad)`} />
      {/* Craters */}
      <circle cx="40" cy="42" r="3" fill="rgba(0,0,0,0.06)" />
      <circle cx="55" cy="50" r="2" fill="rgba(0,0,0,0.04)" />
      <circle cx="45" cy="58" r="2.5" fill="rgba(0,0,0,0.05)" />
      {/* Shadow edge (crescent) */}
      <path d="M 50 28 A 22 22 0 0 0 50 72 A 18 18 0 0 1 50 28" fill="rgba(0,0,0,0.1)" />
    </svg>
  );
}

// ─── Night with clouds ─────────────────────────────────────────────────────

function CloudMoonSVG({ w }: { w: number }) {
  return (
    <svg viewBox="0 0 100 80" width={w} height={w * 0.8} className="overflow-visible">
      <circle cx="80" cy="16" r="1" fill="white">
        <animate attributeName="opacity" values="0.3;1;0.3" dur="2.4s" repeatCount="indefinite" />
      </circle>
      <circle cx="28" cy="22" r="14" fill="#d4d4e0" />
      <circle cx="28" cy="22" r="20" fill="rgba(212,212,224,0.1)" />
      <g transform="translate(0, 0)">
        <animateTransform attributeName="transform" type="translate" values="0,0;6,0;0,0" dur="14s" repeatCount="indefinite" />
        <CloudSVG w={w * 0.8} color="#3a3a48" dark />
      </g>
    </svg>
  );
}

// ─── Main component ────────────────────────────────────────────────────────

export const WeatherDisplay = React.memo(function WeatherDisplay({
  kind,
  size = 'md',
  isNight = false,
  className,
}: WeatherIconProps) {
  const w = sizeMap[size];

  const icon = useMemo(() => {
    if (isNight && kind === 'cloud') return <CloudMoonSVG w={w} />;
    if (isNight && kind === 'sun') return <MoonSVG w={w} />;
    switch (kind) {
      case 'sun': return <SunSVG w={w} />;
      case 'cloud': return <CloudSunSVG w={w} />;
      case 'rain': return <RainSVG w={w} isNight={isNight} />;
      case 'snow': return <SnowSVG w={w} isNight={isNight} />;
      case 'storm': return <StormSVG w={w} isNight={isNight} />;
      default: return <CloudSunSVG w={w} />;
    }
  }, [kind, isNight, w]);

  return (
    <div
      className={cn('flex items-center justify-center shrink-0', className)}
      role="img"
      aria-label={`Tempo: ${kind}${isNight ? ' (noite)' : ''}`}
    >
      {icon}
    </div>
  );
});

// ─── Convenience: code-based wrapper ───────────────────────────────────────

import { getWeatherKind } from '../types';

export function WeatherIconByCode({
  code,
  size = 'md',
  isNight = false,
  className,
}: {
  code: number;
  size?: WeatherIconSize;
  isNight?: boolean;
  className?: string;
}) {
  const kind = getWeatherKind(code);
  return (
    <WeatherDisplay kind={kind} size={size} isNight={isNight} className={className} />
  );
}