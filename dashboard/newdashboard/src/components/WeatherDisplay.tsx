import React, { useMemo } from 'react';

type WeatherKind = 'sun' | 'cloud' | 'rain' | 'snow' | 'storm';

interface WeatherDisplayProps {
  kind: WeatherKind;
  temp?: string | number;
  className?: string;
}

// ─── Individual weather illustrations ───────────────────────────────────────

function SunIcon() {
  return (
    <div className="relative w-full h-full flex items-center justify-center">
      {/* Outer glow */}
      <div className="absolute w-[140%] h-[140%] rounded-full bg-[radial-gradient(circle,rgba(255,200,50,0.12)_0%,rgba(255,200,50,0.04)_40%,transparent_70%)]" />

      {/* Main glow */}
      <div
        className="absolute w-[120%] h-[120%] rounded-full animate-pulse"
        style={{
          background: 'radial-gradient(circle, rgba(255,200,50,0.16) 0%, rgba(255,180,40,0.05) 50%, transparent 70%)',
          animationDuration: '3s',
        }}
      />

      {/* Sun body */}
      <div
        className="relative w-[70%] h-[70%] rounded-full"
        style={{
          background: 'radial-gradient(circle at 35% 35%, #fff8e1 0%, #ffd54f 30%, #ffb300 60%, #ff8f00 100%)',
          boxShadow: '0 0 40px rgba(255, 200, 50, 0.5), 0 0 80px rgba(255, 180, 40, 0.25), inset 0 -2px 6px rgba(0,0,0,0.1)',
        }}
      >
        {/* Surface detail (subtle texture) */}
        <div
          className="absolute inset-[15%] rounded-full opacity-40"
          style={{
            background: 'radial-gradient(circle at 60% 40%, rgba(255,255,255,0.6) 0%, transparent 60%)',
          }}
        />
      </div>

      {/* Soft rays */}
      {Array.from({ length: 12 }, (_, i) => (
        <div
          key={i}
          className="absolute inset-0 flex items-center justify-center"
          style={{ transform: `rotate(${i * 30}deg)` }}
        >
          <div
            className="w-[2px] rounded-full"
            style={{
              height: '55%',
              background: 'linear-gradient(to top, transparent 0%, rgba(255,200,100,0.35) 40%, rgba(255,200,100,0.7) 60%, rgba(255,230,180,0.4) 100%)',
              transform: 'translateY(-10%)',
              animation: `sunRay 4s ${i * 0.15}s ease-in-out infinite`,
            }}
          />
        </div>
      ))}
    </div>
  );
}

function CloudSunIcon() {
  return (
    <div className="relative w-full h-full overflow-hidden">
      {/* Sun behind clouds */}
      <div className="absolute inset-0 scale-75">
        <SunIcon />
      </div>

      {/* Clouds layer 1 (slower, behind) */}
      <div className="absolute inset-0 flex items-center" style={{ animation: 'cloudDrift 12s ease-in-out infinite' }}>
        <CloudShape className="w-[85%] h-auto" opacity={0.65} color="#8a8a96" />
      </div>

      {/* Clouds layer 2 (faster, front) */}
      <div className="absolute inset-0 flex items-center justify-end" style={{ animation: 'cloudDrift2 8s ease-in-out infinite' }}>
        <CloudShape className="w-[60%] h-auto mr-[-10%]" opacity={0.75} color="#a0a0b0" />
      </div>

      {/* Small cloud accent */}
      <div className="absolute bottom-[15%] left-[5%]" style={{ animation: 'cloudDrift 10s ease-in-out infinite' }}>
        <CloudShape className="w-[40%] h-auto" opacity={0.5} color="#7a7a88" />
      </div>
    </div>
  );
}

function RainIcon() {
  return (
    <div className="relative w-full h-full flex flex-col items-center justify-start pt-[5%]">
      {/* Dark cloud */}
      <div className="relative z-10 w-[90%] shrink-0" style={{ filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.3))' }}>
        <CloudShape color="#3a3a48" opacity={1} />
      </div>

      {/* Rain streaks */}
      <div className="absolute inset-0 top-[35%] overflow-hidden">
        {Array.from({ length: 14 }, (_, i) => (
          <div
            key={i}
            className="absolute rounded-full"
            style={{
              left: `${5 + (i * 7) % 90}%`,
              width: '1.5px',
              height: `${12 + (i % 3) * 6}px`,
              background: `linear-gradient(to bottom, rgba(180,200,230,0.1), rgba(180,200,230,0.6))`,
              animation: `rainDrop ${0.7 + (i % 5) * 0.1}s ${(i * 0.12)}s ease-in infinite`,
              opacity: 0.7 + (i % 3) * 0.1,
            }}
          />
        ))}
      </div>

      {/* Rain splashes at bottom */}
      <div className="absolute bottom-[5%] left-0 right-0 h-[15%] overflow-hidden">
        {Array.from({ length: 6 }, (_, i) => (
          <div
            key={i}
            className="absolute bottom-0 rounded-full"
            style={{
              left: `${10 + i * 16}%`,
              width: '2px',
              height: `${4 + (i % 3) * 3}px`,
              background: 'rgba(180,200,230,0.3)',
              animation: `splash 0.6s ${i * 0.2}s ease-out infinite`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

function SnowIcon() {
  return (
    <div className="relative w-full h-full flex flex-col items-center justify-start pt-[5%]">
      <div className="relative z-10 w-[85%] shrink-0 opacity-80">
        <CloudShape color="#6a6a78" opacity={0.8} />
      </div>
      <div className="absolute inset-0 top-[30%] overflow-hidden">
        {Array.from({ length: 18 }, (_, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-white/80"
            style={{
              left: `${8 + (i * 5.5) % 84}%`,
              width: `${2 + (i % 3)}px`,
              height: `${2 + (i % 3)}px`,
              animation: `snowFall ${2.5 + (i % 4) * 0.5}s ${(i * 0.3)}s ease-in infinite`,
              opacity: 0.5 + (i % 4) * 0.1,
            }}
          />
        ))}
      </div>
    </div>
  );
}

function StormIcon() {
  return (
    <div className="relative w-full h-full flex flex-col items-center justify-start pt-[5%]">
      {/* Very dark storm cloud */}
      <div className="relative z-10 w-[95%] shrink-0" style={{ filter: 'drop-shadow(0 6px 20px rgba(0,0,0,0.5))' }}>
        <CloudShape color="#1a1a28" opacity={1} />
      </div>

      {/* Cloud glow base */}
      <div className="absolute top-[5%] left-[10%] right-[10%] h-[30%] rounded-full bg-[radial-gradient(ellipse,rgba(40,40,60,0.6)_0%,transparent_70%)]" />

      {/* Lightning bolt */}
      <div className="absolute top-[15%] left-0 right-0 flex items-start justify-center z-20">
        <svg width="40" height="70" viewBox="0 0 40 70" className="overflow-visible">
          <defs>
            <filter id="lightningGlow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <polygon
            points="22,0 8,35 20,35 14,68 34,28 22,28 28,0"
            fill="#fff8e1"
            opacity="0.95"
            filter="url(#lightningGlow)"
            style={{ animation: 'lightningFlash 4s ease-in-out infinite' }}
          />
        </svg>
      </div>

      {/* Background flash */}
      <div
        className="absolute inset-0 rounded-2xl"
        style={{
          background: 'radial-gradient(ellipse at 50% 20%, rgba(255,250,210,0.15) 0%, transparent 60%)',
          animation: 'stormFlash 4s ease-in-out infinite',
        }}
      />

      {/* Rain */}
      <div className="absolute inset-0 top-[30%] overflow-hidden">
        {Array.from({ length: 18 }, (_, i) => (
          <div
            key={i}
            className="absolute rounded-full"
            style={{
              left: `${3 + (i * 6) % 94}%`,
              width: '1.5px',
              height: `${10 + (i % 4) * 5}px`,
              background: `linear-gradient(to bottom, rgba(160,180,210,0.1), rgba(160,180,210,0.5))`,
              animation: `rainDrop ${0.5 + (i % 3) * 0.1}s ${(i * 0.08)}s ease-in infinite`,
              opacity: 0.6,
            }}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Shared cloud shape (SVG-based for crisp rendering) ────────────────────

function CloudShape({ className, opacity = 0.7, color = '#888' }: {
  className?: string;
  opacity?: number;
  color?: string;
}) {
  return (
    <svg
      viewBox="0 0 120 72"
      className={className}
      style={{ opacity }}
      aria-hidden="true"
    >
      <defs>
        <filter id="cloudBlur">
          <feGaussianBlur stdDeviation="1.5" />
        </filter>
      </defs>
      <ellipse cx="60" cy="52" rx="58" ry="20" fill={color} filter="url(#cloudBlur)" />
      <ellipse cx="30" cy="44" rx="28" ry="24" fill={color} filter="url(#cloudBlur)" />
      <ellipse cx="88" cy="46" rx="26" ry="22" fill={color} filter="url(#cloudBlur)" />
      <ellipse cx="50" cy="34" rx="22" ry="20" fill={color} filter="url(#cloudBlur)" />
      <ellipse cx="74" cy="36" rx="20" ry="18" fill={color} filter="url(#cloudBlur)" />
      <ellipse cx="60" cy="28" rx="16" ry="14" fill={color} filter="url(#cloudBlur)" />
    </svg>
  );
}

// ─── Main component ────────────────────────────────────────────────────────

export const WeatherDisplay = React.memo(function WeatherDisplay({
  kind,
  temp,
  className = '',
}: WeatherDisplayProps) {
  const IconComponent = useMemo(() => {
    switch (kind) {
      case 'sun': return <SunIcon />;
      case 'cloud': return <CloudSunIcon />;
      case 'rain': return <RainIcon />;
      case 'snow': return <SnowIcon />;
      case 'storm': return <StormIcon />;
      default: return <CloudSunIcon />;
    }
  }, [kind]);

  return (
    <div
      className={`relative flex items-center justify-center ${className}`}
      style={{ width: '100%', height: '100%' }}
      role="img"
      aria-label={`Tempo: ${kind}`}
    >
      {/* Container for the illustration */}
      <div className="absolute inset-0 flex items-center justify-center">
        {IconComponent}
      </div>
    </div>
  );
});

// ─── Fallback icon for the OverviewTab weather widget ───────────────────────

export function CompactWeatherIcon({ kind, temp }: { kind: string; temp?: string | number }) {
  return (
    <div className="relative w-14 h-14 shrink-0">
      <WeatherDisplay kind={kind as WeatherKind} temp={temp} />
    </div>
  );
}
